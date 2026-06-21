"""Record one run with a real local model (Ollama), then replay it — byte-identical.

This is the live-model counterpart to run_demo.py: it proves the determinism is not an
artifact of the stub. A real, stochastic open model writes the decision once (during
RECORD); REPLAY reproduces that exact decision and audit trail from the log, with no
model call.

Setup:
    1. Install Ollama:           https://ollama.com
    2. Pull a model:             ollama pull llama3.2
    3. pip install ollama
Run:
    PYTHONPATH=src python3 examples/run_live.py
"""

from __future__ import annotations

from pathlib import Path

from auditable_agents.event_store import EventStore
from auditable_agents.record_replay import Mode
from auditable_agents.workflow import run_trade_preapproval, audit_for

from ollama_model import ollama_model  # same directory

REQUEST = {"account_id": "ACC-001", "symbol": "AAPL", "side": "BUY",
           "quantity": 10_000, "notional_usd": 2_100_000}
LOG = "live.events.jsonl"


def main() -> None:
    Path(LOG).unlink(missing_ok=True)

    # RECORD: exactly one real model call.
    store = EventStore(LOG)
    decision = run_trade_preapproval(REQUEST, store, Mode.RECORD, model=ollama_model)
    recorded = audit_for(store)
    print("=== RECORDED (one real Ollama call) ===")
    print(recorded)

    # REPLAY: no model call; the recorded output is reused.
    replay_store = EventStore(LOG)
    replay_decision = run_trade_preapproval(REQUEST, replay_store, Mode.REPLAY, model=ollama_model)
    replayed = audit_for(replay_store)

    identical = decision == replay_decision and recorded == replayed
    print("\n=== REPLAY byte-identical to the recording? ===", "YES" if identical else "NO")


if __name__ == "__main__":
    main()
