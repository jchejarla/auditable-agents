"""Generate the three scenarios used as figures in the paper.

Each scenario is recorded, then replayed 3x, and asserted byte-identical:

  1. APPROVE   — a clean trade the agent approves; order reserved + submitted.
  2. REJECT    — a trade over the exposure limit; the agent rejects it (no saga).
  3. ROLLBACK  — an approved trade whose execution fails; the reservation is
                 compensated (rolled back) and recorded in the audit trail.

Run:  PYTHONPATH=src python examples/run_scenarios.py
"""

from __future__ import annotations

import random
from pathlib import Path

from auditable_agents.event_store import EventStore
from auditable_agents.record_replay import Mode
from auditable_agents.workflow import run_trade_preapproval, audit_for

OUT = Path("scenarios")

SCENARIOS = [
    ("approve", {"account_id": "ACC-001", "symbol": "AAPL", "side": "BUY",
                 "quantity": 10_000, "notional_usd": 2_100_000}, None),
    ("reject",  {"account_id": "ACC-002", "symbol": "AAPL", "side": "BUY",
                 "quantity": 50_000, "notional_usd": 9_000_000}, None),   # over 5M limit
    ("rollback", {"account_id": "ACC-003", "symbol": "AAPL", "side": "BUY",
                  "quantity": 10_000, "notional_usd": 2_100_000}, "venue"),  # exec fails
]


def run_one(name: str, request: dict, fault: str | None) -> None:
    OUT.mkdir(exist_ok=True)
    log = OUT / f"{name}.events.jsonl"
    log.unlink(missing_ok=True)

    # The model stub is stochastic; seed it so this paper's figures are reproducible.
    # (Replay never calls the model, so seeding only affects the recording run.)
    random.seed(name)

    # record
    store = EventStore(log)
    decision = run_trade_preapproval(request, store, Mode.RECORD, fault=fault)
    audit = audit_for(store)

    # replay 3x, assert identical
    identical = True
    for _ in range(3):
        s = EventStore(log)
        d = run_trade_preapproval(request, s, Mode.REPLAY, fault=fault)
        if d != decision or audit_for(s) != audit:
            identical = False

    print(f"\n########## SCENARIO: {name.upper()}  (replay identical: {identical}) ##########")
    print("DECISION:", decision)
    print(audit)
    (OUT / f"{name}.audit.txt").write_text(audit + "\n")


def main() -> None:
    for name, request, fault in SCENARIOS:
        run_one(name, request, fault)
    print(f"\nLogs + audit trails written to ./{OUT}/")


if __name__ == "__main__":
    main()
