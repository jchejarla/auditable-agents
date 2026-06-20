"""Optional: use a local open-source model (via Ollama) as the agent's decision step.

Free, local, no API key, open weights — and fully reproducible by anyone. This is the
recommended way to validate the layer against a real, stochastic model.

Setup:
    1. Install Ollama:           https://ollama.com
    2. Pull a small open model:  ollama pull llama3.2     (or qwen2.5, mistral, phi3)
    3. pip install ollama

Use it via the workflow's pluggable model= argument:

    from auditable_agents.event_store import EventStore
    from auditable_agents.record_replay import Mode
    from auditable_agents.workflow import run_trade_preapproval, audit_for
    from examples.ollama_model import ollama_model

    request = {"account_id": "ACC-001", "symbol": "AAPL", "side": "BUY",
               "quantity": 10_000, "notional_usd": 2_100_000}
    store = EventStore("live.events.jsonl")
    run_trade_preapproval(request, store, Mode.RECORD, model=ollama_model)  # one real call
    print(audit_for(store))

    # replay reproduces the recorded completion byte-for-byte, with no model call:
    run_trade_preapproval(request, EventStore("live.events.jsonl"), Mode.REPLAY)

Because record-replay captures the model's output once, a real (stochastic) open model
replays byte-for-byte exactly as the stub does.
"""

from __future__ import annotations

import json
from typing import Any

import ollama  # optional dependency; only needed to use a local model

MODEL = "llama3.2"  # any locally pulled model: qwen2.5, mistral, phi3, ...

_DECISION_SCHEMA = {
    "type": "object",
    "properties": {
        "decision": {"type": "string", "enum": ["APPROVE", "REJECT"]},
        "rationale": {"type": "string"},
        "confidence": {"type": "number"},
    },
    "required": ["decision", "rationale", "confidence"],
}

_SYSTEM = (
    "You are a trade pre-approval assistant. Using only the compliance and exposure "
    "results in the message, decide APPROVE or REJECT, give a one-sentence rationale, "
    "and a confidence score between 0 and 1."
)


def ollama_model(prompt: str, tool_results: dict[str, Any]) -> dict[str, Any]:
    """A local-LLM drop-in for the stub. Returns {decision, rationale, confidence}."""
    response = ollama.chat(
        model=MODEL,
        messages=[{"role": "system", "content": _SYSTEM},
                  {"role": "user", "content": prompt}],
        format=_DECISION_SCHEMA,        # structured output (Ollama >= 0.5)
        options={"temperature": 0.8},   # keep it stochastic, like a real deployment
    )
    return json.loads(response["message"]["content"])
