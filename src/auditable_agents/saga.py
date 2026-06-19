"""Run side-effecting steps, rolling back the completed ones if a later step fails.

Each step pairs an action with its compensation. The action, any failure, and the
compensations are all logged, so a rollback shows up in the audit trail just like a
success. No-op on replay — the outcomes are already in the log.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from .event_store import EventStore
from .record_replay import Mode


@dataclass
class SagaStep:
    name: str
    action: Callable[[], None]
    compensation: Callable[[], None]


class Saga:
    def __init__(self, store: EventStore, mode: Mode):
        self.store = store
        self.mode = mode

    def run(self, steps: list[SagaStep]) -> None:
        if self.mode is Mode.REPLAY:
            return

        done: list[SagaStep] = []
        for s in steps:
            if self.store.find(f"saga:{s.name}") is not None:  # completed on a prior attempt
                done.append(s)
                continue
            try:
                s.action()
            except Exception as exc:
                self.store.append(s.name, f"fail:{s.name}", "saga_failure",
                                  {"name": s.name, "error": str(exc)})
                for d in reversed(done):  # undo completed steps, newest first
                    d.compensation()
                    self.store.append(d.name, f"comp:{d.name}", "compensation",
                                      {"name": d.name, "status": "compensated"})
                raise
            self.store.append(s.name, f"saga:{s.name}", "saga_action",
                              {"name": s.name, "status": "completed"})
            done.append(s)
