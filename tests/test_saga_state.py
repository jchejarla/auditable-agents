"""The saga moves real state, and compensation restores it.

On a successful approve, buying power is reduced and stays reduced. On a rollback
(submission fails), the reservation is released and buying power returns to its
starting value — visible as a compensation event in the log, not just a label.
"""

from __future__ import annotations

from pathlib import Path

from auditable_agents.event_store import EventStore
from auditable_agents.record_replay import Mode
from auditable_agents.workflow import run_trade_preapproval, INITIAL_BUYING_POWER_USD

REQ = {"account_id": "ACC-001", "symbol": "AAPL", "side": "BUY",
       "quantity": 10_000, "notional_usd": 2_100_000}


def _events(log: Path):
    return EventStore(log).read_all()


def test_successful_approve_reduces_buying_power(tmp_path: Path):
    log = tmp_path / "ok.jsonl"
    run_trade_preapproval(REQ, EventStore(log), Mode.RECORD)
    reserve = next(e for e in _events(log)
                   if e.kind == "saga_action" and e.step_id == "reserve_buying_power")
    assert reserve.payload["buying_power"] == INITIAL_BUYING_POWER_USD - REQ["notional_usd"]
    assert not any(e.kind == "compensation" for e in _events(log))


def test_rollback_restores_buying_power(tmp_path: Path):
    log = tmp_path / "rb.jsonl"
    run_trade_preapproval(REQ, EventStore(log), Mode.RECORD, fault="venue")
    comp = next(e for e in _events(log) if e.kind == "compensation")
    assert comp.payload["buying_power"] == INITIAL_BUYING_POWER_USD  # released back to start
