"""Record-replay actually does work: without it, runs diverge; with it, they don't.

The model stub is stochastic (a per-call confidence score). Two independent recorded
runs of the same request therefore produce different audit trails — that is what an
unguarded, re-run agent looks like. Replaying a recorded run reproduces it exactly,
regardless of the current random state. This is the contrast the whole approach rests on.
"""

from __future__ import annotations

import random
from pathlib import Path

from auditable_agents.event_store import EventStore
from auditable_agents.record_replay import Mode
from auditable_agents.workflow import run_trade_preapproval, audit_for

REQ = {"account_id": "ACC-001", "symbol": "AAPL", "side": "BUY",
       "quantity": 10_000, "notional_usd": 2_100_000}


def test_independent_runs_diverge_but_replay_reproduces(tmp_path: Path):
    # two independent recordings of the same request, different random state
    random.seed(1)
    log_a = tmp_path / "a.jsonl"
    run_trade_preapproval(REQ, EventStore(log_a), Mode.RECORD)
    audit_a = audit_for(EventStore(log_a))

    random.seed(2)
    log_b = tmp_path / "b.jsonl"
    run_trade_preapproval(REQ, EventStore(log_b), Mode.RECORD)
    audit_b = audit_for(EventStore(log_b))

    # without replay, the stochastic model makes the two runs diverge
    assert audit_a != audit_b

    # replaying run A reproduces A exactly, whatever the RNG is doing now
    random.seed(999)
    assert audit_for_after_replay(log_a) == audit_a


def audit_for_after_replay(log: Path) -> str:
    store = EventStore(log)
    run_trade_preapproval(REQ, store, Mode.REPLAY)
    return audit_for(store)
