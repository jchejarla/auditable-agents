"""The agent's one non-deterministic step: ask the model to decide.

Goes through record-replay, so the model is hit once and replayed afterward. To use
a real LLM, replace the body of _decide with a provider call that returns a dict;
the deterministic stub here is enough to exercise the machinery.
"""

from __future__ import annotations

from typing import Any

from .record_replay import RecordReplay


def model_reason(rr: RecordReplay, idempotency_key: str, prompt: str,
                 tool_results: dict[str, Any]) -> dict[str, Any]:
    def _decide() -> dict[str, Any]:
        compliance = tool_results["compliance"]
        exposure = tool_results["exposure"]
        if compliance["passed"] and exposure["within_limit"]:
            return {"decision": "APPROVE",
                    "rationale": "Compliance checks passed and trade is within the exposure limit."}
        reasons = []
        if not compliance["passed"]:
            reasons.append(f"compliance violations: {compliance['violations']}")
        if not exposure["within_limit"]:
            reasons.append(f"exposure exceeds limit (headroom {exposure['headroom']})")
        return {"decision": "REJECT", "rationale": "; ".join(reasons)}

    return rr.call("model_reason", idempotency_key, "model_call", _decide,
                   {"prompt": prompt})
