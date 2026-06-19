"""Run side-effecting steps, rolling back the completed ones if a later step fails.

Each step pairs an action with its compensation; either may return a dict of detail
(e.g., a resulting balance) that is recorded with the event. The action, any failure,
and the compensations are all logged, so a rollback shows up in the audit trail just
like a success. Keys are scoped by a per-request run key, so a resumed run reuses its
own completed steps and nothing else. No-op on replay — the outcomes are already logged.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from .event_store import EventStore
from .record_replay import Mode


@dataclass
class SagaStep:
    name: str
    action: Callable[[], "dict[str, Any] | None"]
    compensation: Callable[[], "dict[str, Any] | None"]


class Saga:
    def __init__(self, store: EventStore, mode: Mode, run_key: str = ""):
        self.store = store
        self.mode = mode
        self.run_key = run_key

    def run(self, steps: list[SagaStep]) -> None:
        if self.mode is Mode.REPLAY:
            return

        done: list[SagaStep] = []
        for s in steps:
            saga_key = f"saga:{self.run_key}:{s.name}"
            if self.store.find(saga_key) is not None:  # completed on a prior attempt
                done.append(s)
                continue
            try:
                detail = s.action() or {}
            except Exception as exc:
                self.store.append(s.name, f"fail:{self.run_key}:{s.name}", "saga_failure",
                                  {"name": s.name, "error": str(exc)})
                for d in reversed(done):  # undo completed steps, newest first
                    cdetail = d.compensation() or {}
                    self.store.append(d.name, f"comp:{self.run_key}:{d.name}", "compensation",
                                      {"name": d.name, "status": "compensated", **cdetail})
                raise
            self.store.append(s.name, saga_key, "saga_action",
                              {"name": s.name, "status": "completed", **detail})
            done.append(s)
