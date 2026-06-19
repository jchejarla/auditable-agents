"""Overhead benchmark for the durable layer.

Compares three modes on the same trade-pre-approval workflow:
  baseline : the agent logic with NO durable layer (no logging/replay/saga)
  record   : full durable workflow, first run (writes the event log)
  replay   : full durable workflow, replaying from the log (no model/tool calls)

Reports average per-run latency and the event-log size. The stub "model" is
instant, so these numbers isolate the *durable-layer* overhead itself; against a
real LLM call (hundreds of ms to seconds) this overhead is negligible.

Run:  PYTHONPATH=src python examples/bench.py
"""

from __future__ import annotations

import tempfile
import time
from pathlib import Path

from auditable_agents.event_store import EventStore
from auditable_agents.record_replay import Mode
from auditable_agents.workflow import (
    run_trade_preapproval, compliance_check, exposure_check,
)

REQUEST = {"account_id": "ACC-001", "symbol": "AAPL", "side": "BUY",
           "quantity": 10_000, "notional_usd": 2_100_000}
N = 2000


def baseline(request: dict) -> dict:
    """Same decision logic, with no durable layer at all."""
    c = compliance_check(request)
    e = exposure_check(request)
    approve = c["passed"] and e["within_limit"]
    return {
        "account_id": request["account_id"],
        "symbol": request["symbol"],
        "decision": "APPROVE" if approve else "REJECT",
    }


def avg_us(fn, n: int) -> float:
    t0 = time.perf_counter()
    for _ in range(n):
        fn()
    return (time.perf_counter() - t0) / n * 1e6  # microseconds/run


def main() -> None:
    with tempfile.TemporaryDirectory() as d:
        log = Path(d) / "bench.events.jsonl"

        # baseline
        b = avg_us(lambda: baseline(REQUEST), N)

        # record (fresh log each run)
        def _record():
            log.unlink(missing_ok=True)
            run_trade_preapproval(REQUEST, EventStore(log), Mode.RECORD)
        r = avg_us(_record, N)

        # measure log size for one recorded run
        log.unlink(missing_ok=True)
        run_trade_preapproval(REQUEST, EventStore(log), Mode.RECORD)
        size = log.stat().st_size
        events = sum(1 for _ in log.read_text().splitlines() if _.strip())

        # replay (reuse the recorded log)
        rp = avg_us(lambda: run_trade_preapproval(REQUEST, EventStore(log), Mode.REPLAY), N)

    print(f"runs per mode: {N}")
    print(f"{'baseline (no layer)':<28} {b:8.1f} us/run")
    print(f"{'record (durable)':<28} {r:8.1f} us/run   (+{r - b:.1f} us overhead)")
    print(f"{'replay (durable)':<28} {rp:8.1f} us/run")
    print(f"event log: {events} events, {size} bytes")


if __name__ == "__main__":
    main()
