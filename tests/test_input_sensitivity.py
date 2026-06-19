"""Idempotency keys depend on inputs, not just identity.

A different request must never reuse a prior request's recorded decision, even on the
same account — keys are scoped to a hash of the request, not the account alone.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from auditable_agents.event_store import EventStore
from auditable_agents.record_replay import Mode
from auditable_agents.workflow import run_trade_preapproval

APPROVE_REQ = {"account_id": "ACC-1", "symbol": "AAPL", "side": "BUY",
               "quantity": 1_000, "notional_usd": 2_000_000}
# same account, but a far larger trade that should be rejected
REJECT_REQ = {"account_id": "ACC-1", "symbol": "AAPL", "side": "BUY",
              "quantity": 1_000, "notional_usd": 9_000_000}


def test_different_request_does_not_reuse_prior_decision(tmp_path: Path):
    log = tmp_path / "log.jsonl"
    a = run_trade_preapproval(APPROVE_REQ, EventStore(log), Mode.RECORD)
    b = run_trade_preapproval(REJECT_REQ, EventStore(log), Mode.RECORD)
    assert a["decision"] == "APPROVE"
    assert b["decision"] == "REJECT"  # reflects B's inputs, not A's stale result


def test_replay_of_unrecorded_request_raises(tmp_path: Path):
    log = tmp_path / "log.jsonl"
    run_trade_preapproval(APPROVE_REQ, EventStore(log), Mode.RECORD)
    with pytest.raises(KeyError):
        run_trade_preapproval(REJECT_REQ, EventStore(log), Mode.REPLAY)
