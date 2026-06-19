"""Append-only event log: the source of truth and the audit trail.

Each step appends one immutable event; the run is reproduced by replaying the log
and audited by rendering it. JSON-lines on disk, ordered by sequence number (never
wall-clock) so replays come out identical.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Iterator


@dataclass(frozen=True)
class Event:
    seq: int
    step_id: str
    idempotency_key: str
    kind: str  # model_call | tool_call | decision | saga_action | saga_failure | compensation
    payload: dict[str, Any]


class EventStore:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self._events: list[Event] = []
        self._next_seq = 0
        if self.path.exists():  # resume / replay from an existing log
            for line in self.path.read_text().splitlines():
                line = line.strip()
                if line:
                    self._events.append(Event(**json.loads(line)))
            if self._events:
                self._next_seq = self._events[-1].seq + 1

    def append(self, step_id: str, idempotency_key: str, kind: str,
               payload: dict[str, Any]) -> Event:
        ev = Event(self._next_seq, step_id, idempotency_key, kind, payload)
        self._next_seq += 1
        with self.path.open("a") as f:
            f.write(json.dumps(asdict(ev), sort_keys=True) + "\n")
        self._events.append(ev)
        return ev

    def read_all(self) -> list[Event]:
        return list(self._events)

    def find(self, idempotency_key: str) -> Event | None:
        for ev in self._events:  # linear scan is fine at this size
            if ev.idempotency_key == idempotency_key:
                return ev
        return None

    def __iter__(self) -> Iterator[Event]:
        return iter(self._events)
