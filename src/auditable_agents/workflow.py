"""The demo workflow: AI-assisted trade pre-approval.

Wires the pieces together: the tools and the model call go through record-replay, the
order actions go through a saga, and the final decision is a durable step. Pass
fault="venue" to make order submission fail and exercise the rollback path.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

from .agent import model_reason
from .audit import render_audit
from .event_store import EventStore
from .record_replay import RecordReplay, Mode
from .runner import DurableRunner
from .saga import Saga, SagaStep

RESTRICTED_SYMBOLS = {"RESTRICTEDCO"}
EXPOSURE_LIMIT_USD = 5_000_000


def _request_key(request: dict[str, Any]) -> str:
    """Stable short hash of the request, so step keys depend on inputs, not just identity."""
    return hashlib.sha1(json.dumps(request, sort_keys=True).encode()).hexdigest()[:12]


def compliance_check(request: dict[str, Any]) -> dict[str, Any]:
    violations = []
    if request["symbol"] in RESTRICTED_SYMBOLS:
        violations.append(f"{request['symbol']} is on the restricted list")
    if request["side"] not in ("BUY", "SELL"):
        violations.append(f"invalid side {request['side']!r}")
    return {"passed": not violations, "violations": violations}


def exposure_check(request: dict[str, Any]) -> dict[str, Any]:
    notional = request["notional_usd"]
    return {"within_limit": notional <= EXPOSURE_LIMIT_USD,
            "headroom": EXPOSURE_LIMIT_USD - notional}


def run_trade_preapproval(request: dict[str, Any], store: EventStore,
                          mode: Mode, fault: str | None = None) -> dict[str, Any]:
    rr = RecordReplay(store, mode)
    runner = DurableRunner(store)
    key = _request_key(request)  # step keys are scoped to this exact request

    compliance = rr.call("compliance_check", f"compliance:{key}", "tool_call",
                         lambda: compliance_check(request), {"request": request})
    exposure = rr.call("exposure_check", f"exposure:{key}", "tool_call",
                       lambda: exposure_check(request), {"request": request})

    prompt = (f"Trade request {request}. compliance={compliance} exposure={exposure}. "
              "Decide APPROVE or REJECT with a rationale.")
    reasoning = model_reason(rr, f"model:{key}", prompt,
                             {"compliance": compliance, "exposure": exposure})

    # APPROVE -> reserve buying power, then submit; submission failure rolls the reservation back
    executed: bool | None = None
    if reasoning["decision"] == "APPROVE":
        def _submit() -> None:
            if fault == "venue":
                raise RuntimeError("execution venue rejected the order")
        try:
            Saga(store, mode, key).run([
                SagaStep("reserve_buying_power", lambda: None, lambda: None),
                SagaStep("submit_order", _submit, lambda: None),
            ])
            executed = True
        except Exception:
            executed = False  # saga already compensated the reservation

    def _finalize() -> dict[str, Any]:
        out = {"account_id": request["account_id"], "symbol": request["symbol"],
               "decision": reasoning["decision"], "rationale": reasoning["rationale"]}
        if reasoning["decision"] == "APPROVE":
            out["executed"] = executed
        return out

    return runner.step("finalize_decision", f"finalize:{key}", _finalize)


def audit_for(store: EventStore) -> str:
    return render_audit(store)
