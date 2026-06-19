"""Demo: record a trade-pre-approval run, then replay it deterministically.

    python examples/run_demo.py            # record
    python examples/run_demo.py --replay   # replay; print audit trail

Acceptance goal: the decision and the audit trail are byte-identical across the
record run and every replay.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from auditable_agents.event_store import EventStore
from auditable_agents.record_replay import Mode
from auditable_agents.workflow import run_trade_preapproval, audit_for

LOG_PATH = "run.events.jsonl"

SAMPLE_REQUEST = {
    "account_id": "ACC-001",
    "symbol": "AAPL",
    "side": "BUY",
    "quantity": 10_000,
    "notional_usd": 2_100_000,
}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--replay", action="store_true")
    args = ap.parse_args()

    mode = Mode.REPLAY if args.replay else Mode.RECORD
    if mode is Mode.RECORD:
        Path(LOG_PATH).unlink(missing_ok=True)  # start a fresh log when recording
    store = EventStore(LOG_PATH)

    decision = run_trade_preapproval(SAMPLE_REQUEST, store, mode)
    print("DECISION:", decision)
    print("\n--- AUDIT TRAIL ---")
    print(audit_for(store))


if __name__ == "__main__":
    main()
