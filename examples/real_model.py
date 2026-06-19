"""Optional: use a real Claude model as the agent's decision step.

The workflow's model is just a callable, so a real LLM drops in with no other change:

    from auditable_agents.event_store import EventStore
    from auditable_agents.record_replay import Mode
    from auditable_agents.workflow import run_trade_preapproval, audit_for
    from examples.real_model import claude_model

    request = {"account_id": "ACC-001", "symbol": "AAPL", "side": "BUY",
               "quantity": 10_000, "notional_usd": 2_100_000}
    store = EventStore("run.events.jsonl")
    run_trade_preapproval(request, store, Mode.RECORD, model=claude_model)  # one real call
    print(audit_for(store))

    # later — replay reproduces the recorded decision exactly, with no model call:
    run_trade_preapproval(request, EventStore("run.events.jsonl"), Mode.REPLAY)

Record-replay captures the model's (stochastic) output on the recording run, so every
replay reproduces it byte-for-byte — the whole point of the pattern, now with a real model.

Requires:  pip install anthropic   and   export ANTHROPIC_API_KEY=...
"""

from __future__ import annotations

import json
from typing import Any

import anthropic  # optional dependency; only needed to use a real model

_client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY from the environment

_DECISION_SCHEMA = {
    "type": "object",
    "properties": {
        "decision": {"type": "string", "enum": ["APPROVE", "REJECT"]},
        "rationale": {"type": "string"},
        "confidence": {"type": "number"},
    },
    "required": ["decision", "rationale", "confidence"],
    "additionalProperties": False,
}

_SYSTEM = (
    "You are a trade pre-approval assistant. Using only the compliance and exposure "
    "results in the message, decide APPROVE or REJECT, give a one-sentence rationale, "
    "and a confidence score between 0 and 1."
)


def claude_model(prompt: str, tool_results: dict[str, Any]) -> dict[str, Any]:
    """A real-LLM drop-in for the stub. Returns {decision, rationale, confidence}."""
    response = _client.messages.create(
        model="claude-opus-4-8",
        max_tokens=1024,
        system=_SYSTEM,
        messages=[{"role": "user", "content": prompt}],
        output_config={"format": {"type": "json_schema", "schema": _DECISION_SCHEMA}},
    )
    text = next(block.text for block in response.content if block.type == "text")
    return json.loads(text)
