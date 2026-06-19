"""Exactly-once / crash-safe resumption.

If a run is retried or resumed (e.g., after a crash), steps that already completed
must not run again. We check this at the primitive level and end to end: a second
attempt over the same log re-executes nothing and adds no new events.
"""

from __future__ import annotations

from pathlib import Path

from auditable_agents.event_store import EventStore
from auditable_agents.record_replay import RecordReplay, Mode
from auditable_agents.runner import DurableRunner
from auditable_agents.workflow import run_trade_preapproval

REQ = {"account_id": "ACC-001", "symbol": "AAPL", "side": "BUY",
       "quantity": 10_000, "notional_usd": 2_100_000}


def test_recorded_call_runs_once_across_retries(tmp_path: Path):
    log = tmp_path / "log.jsonl"
    runs = {"n": 0}

    def side_effect():
        runs["n"] += 1
        return {"submitted": True}

    rr1 = RecordReplay(EventStore(log), Mode.RECORD)
    out1 = rr1.call("submit_order", "submit:ACC-1", "tool_call", side_effect, {})
    # crash + restart: a new store over the same log, same step retried
    rr2 = RecordReplay(EventStore(log), Mode.RECORD)
    out2 = rr2.call("submit_order", "submit:ACC-1", "tool_call", side_effect, {})

    assert runs["n"] == 1  # executed exactly once despite the retry
    assert out1 == out2


def test_durable_step_runs_once_across_retries(tmp_path: Path):
    log = tmp_path / "log.jsonl"
    runs = {"n": 0}

    def finalize():
        runs["n"] += 1
        return {"decision": "APPROVE"}

    DurableRunner(EventStore(log)).step("finalize", "finalize:ACC-1", finalize)
    DurableRunner(EventStore(log)).step("finalize", "finalize:ACC-1", finalize)

    assert runs["n"] == 1


def test_workflow_retry_adds_no_new_events(tmp_path: Path):
    log = tmp_path / "log.jsonl"
    d1 = run_trade_preapproval(REQ, EventStore(log), Mode.RECORD)
    n1 = len(EventStore(log).read_all())
    # retry the whole workflow over the same log (simulating a resumed run)
    d2 = run_trade_preapproval(REQ, EventStore(log), Mode.RECORD)
    n2 = len(EventStore(log).read_all())

    assert d1 == d2
    assert n1 == n2  # nothing re-executed, no duplicate side effects
