"""The agent's one non-deterministic step: ask the model to decide.

Routed through record-replay, so the model is hit once and replayed afterward. The stub
emulates a real LLM by drawing a per-call confidence score, so its output genuinely
varies between fresh calls. That variation is what makes record-replay observable: two
unguarded runs diverge, while a replayed run reproduces the recorded output byte for
byte. Replace the body of _decide with a real provider call (returning a dict) to use
an actual model.
"""

from __future__ import annotations

import random
from typing import Any

from .record_replay import RecordReplay


def model_reason(rr: RecordReplay, idempotency_key: str, prompt: str,
                 tool_results: dict[str, Any]) -> dict[str, Any]:
    def _decide() -> dict[str, Any]:
        compliance = tool_results["compliance"]
        exposure = tool_results["exposure"]
        confidence = round(random.uniform(0.50, 0.99), 4)  # varies per call, like a real model
        if compliance["passed"] and exposure["within_limit"]:
            return {"decision": "APPROVE",
                    "rationale": "Compliance checks passed and trade is within the exposure limit.",
                    "confidence": confidence}
        reasons = []
        if not compliance["passed"]:
            reasons.append(f"compliance violations: {compliance['violations']}")
        if not exposure["within_limit"]:
            reasons.append(f"exposure exceeds limit (headroom {exposure['headroom']})")
        return {"decision": "REJECT", "rationale": "; ".join(reasons), "confidence": confidence}

    return rr.call("model_reason", idempotency_key, "model_call", _decide,
                   {"prompt": prompt})
