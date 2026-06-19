"""The agent's one non-deterministic step: ask the model to decide.

The model is a plain callable, `(prompt, tool_results) -> {"decision", "rationale",
"confidence"}`, so it is model-agnostic — the default is an in-process stub, and a real
LLM can be passed in (see examples/real_model.py). Either way the call is routed through
record-replay, so the model runs once and is replayed afterward. The stub draws a
per-call confidence score, so its output varies between calls like a real model's would;
that is what makes record-replay observable.
"""

from __future__ import annotations

import random
from typing import Any, Callable

from .record_replay import RecordReplay

# A model maps (prompt, tool_results) to a decision dict.
Model = Callable[[str, dict[str, Any]], dict[str, Any]]


def stub_model(prompt: str, tool_results: dict[str, Any]) -> dict[str, Any]:
    """Default in-process model: decides from the tool results, with a varying confidence."""
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


def model_reason(rr: RecordReplay, idempotency_key: str, prompt: str,
                 tool_results: dict[str, Any], model: Model | None = None) -> dict[str, Any]:
    fn = model or stub_model
    return rr.call("model_reason", idempotency_key, "model_call",
                   lambda: fn(prompt, tool_results), {"prompt": prompt})
