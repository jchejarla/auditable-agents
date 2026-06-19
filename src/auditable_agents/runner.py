"""Run each step at most once.

Look the step up by its idempotency key before running it; if it already ran, reuse
the recorded result. Gives exactly-once over at-least-once infrastructure and lets a
crashed run resume instead of repeating side effects.
"""

from __future__ import annotations

from typing import Any, Callable

from .event_store import EventStore


class DurableRunner:
    def __init__(self, store: EventStore):
        self.store = store

    def step(self, step_id: str, idempotency_key: str, fn: Callable[[], Any]) -> Any:
        existing = self.store.find(idempotency_key)
        if existing is not None:
            return existing.payload["output"]
        output = fn()
        self.store.append(step_id, idempotency_key, "decision", {"output": output})
        return output
