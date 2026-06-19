"""Render the event log as a human-readable audit trail.

A pure function of the log, so it reproduces whenever the log does. Values are
dumped with sorted keys so RECORD and REPLAY yield byte-identical text.
"""

from __future__ import annotations

import json

from .event_store import EventStore

_BAR = "=" * 64


def _j(obj) -> str:
    return json.dumps(obj, sort_keys=True)


def render_audit(store: EventStore) -> str:
    lines = ["AUDIT TRAIL", _BAR]
    final = None
    for ev in store.read_all():
        p = ev.payload
        if ev.kind == "tool_call":
            lines += [f"[{ev.seq}] {ev.step_id} (tool)",
                      f"      in : {_j(p.get('inputs', {}))}",
                      f"      out: {_j(p.get('output', {}))}"]
        elif ev.kind == "model_call":
            lines += [f"[{ev.seq}] {ev.step_id} (model)",
                      f"      prompt: {p.get('inputs', {}).get('prompt', '')}",
                      f"      out   : {_j(p.get('output', {}))}"]
        elif ev.kind == "saga_action":
            bp = f"  buying_power={p['buying_power']}" if "buying_power" in p else ""
            lines.append(f"[{ev.seq}] {ev.step_id} (saga) -> {p.get('status')}{bp}")
        elif ev.kind == "saga_failure":
            lines.append(f"[{ev.seq}] {ev.step_id} (saga FAILED) -> {p.get('error')}")
        elif ev.kind == "compensation":
            bp = f"  buying_power={p['buying_power']}" if "buying_power" in p else ""
            lines.append(f"[{ev.seq}] {ev.step_id} (compensation) -> {p.get('status')}{bp}")
        elif ev.kind == "decision":
            final = p.get("output")
            lines.append(f"[{ev.seq}] {ev.step_id} (decision) -> {_j(final)}")
    lines += [_BAR, f"FINAL DECISION: {_j(final)}"]
    return "\n".join(lines)
