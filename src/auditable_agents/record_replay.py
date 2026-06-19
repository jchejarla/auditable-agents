"""Record non-deterministic calls once, reuse the recorded result afterwards.

A call runs only if its key is not already in the log. That one rule covers three
cases: REPLAY (return the recorded output), a fresh RECORD run (execute and
record), and a *resumed* RECORD run after a crash (reuse steps that already
completed, so nothing runs twice). The model and external tools therefore run at
most once — which is both what makes a run reproducible and what gives
exactly-once execution.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Callable

from .event_store import EventStore


class Mode(Enum):
    RECORD = "record"
    REPLAY = "replay"


class RecordReplay:
    def __init__(self, store: EventStore, mode: Mode):
        self.store = store
        self.mode = mode

    def call(self, step_id: str, idempotency_key: str, kind: str,
             fn: Callable[[], Any], inputs: dict[str, Any]) -> Any:
        existing = self.store.find(idempotency_key)
        if existing is not None:  # already recorded: replay, or resume after a crash
            return existing.payload["output"]
        if self.mode is Mode.REPLAY:
            raise KeyError(f"nothing recorded to replay for {idempotency_key!r}")

        output = fn()
        self.store.append(step_id, idempotency_key, kind,
                          {"inputs": inputs, "output": output})
        return output
