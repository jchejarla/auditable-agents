"""Core test: a recorded run replays to a byte-identical decision and audit trail."""

from __future__ import annotations

import tempfile
from pathlib import Path

from auditable_agents.event_store import EventStore
from auditable_agents.record_replay import Mode
from auditable_agents.workflow import run_trade_preapproval, audit_for

REQUEST = {
    "account_id": "ACC-001",
    "symbol": "AAPL",
    "side": "BUY",
    "quantity": 10_000,
    "notional_usd": 2_100_000,
}


def test_replay_is_identical():
    with tempfile.TemporaryDirectory() as d:
        log = Path(d) / "run.events.jsonl"

        store = EventStore(log)
        d1 = run_trade_preapproval(REQUEST, store, Mode.RECORD)
        a1 = audit_for(store)

        # Replay from the same log, multiple times.
        for _ in range(3):
            store_r = EventStore(log)
            d2 = run_trade_preapproval(REQUEST, store_r, Mode.REPLAY)
            a2 = audit_for(store_r)
            assert d2 == d1
            assert a2 == a1
