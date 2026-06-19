# auditable-agents

A minimal, single-process **durable, deterministically-replayable execution layer for LLM-agent workflows** — bringing distributed-systems discipline (event sourcing, idempotency, record-replay, sagas) to agentic AI so that decisions are **reproducible and audit-complete**, as required in regulated domains.

> Reference prototype for the article *"Making LLM-Agent Workflows Auditable: Bringing
> Distributed-Systems Discipline to Agentic AI in Regulated Domains"* (in preparation).

## Why

LLM agents are non-deterministic, non-reproducible, and non-auditable — disqualifying in
regulated finance. This prototype shows how four established distributed-systems techniques
combine to fix that:

- **Event sourcing** — every step is an immutable, ordered event; the log *is* the audit trail.
- **Idempotency keys** — steps are replay-safe; re-execution never double-acts.
- **Record-replay** — non-deterministic model/tool responses are recorded once, then replayed
  deterministically (also makes this $0 and cloud-free).
- **Sagas / compensation** — failed multi-step actions roll back via compensating steps.

## Demo workflow

A mock **AI-assisted trade pre-approval**: an agent checks compliance rules and exposure
limits, reasons over them, and emits an APPROVE/REJECT decision with rationale — then the
whole run is replayed to prove byte-identical reproduction and a complete audit trail.

## Scope (intentionally minimal)

Single process. No real cluster, broker, cloud, UI, or multi-agent. The contribution is the
**pattern**, demonstrated end-to-end on a laptop.

## Layout

```
src/auditable_agents/
  event_store.py    # append-only event log (the source of truth + audit trail)
  runner.py         # durable step runner: idempotency, replay-safe execution
  record_replay.py  # record/replay of non-deterministic model & tool calls
  saga.py           # compensation / rollback for multi-step actions
  audit.py          # render a human-readable audit trail from the event log
  agent.py          # the agent loop (LLM reasoning + tool calls)
  workflow.py       # the mock trade-pre-approval workflow
examples/run_demo.py
tests/test_determinism.py
```

## Quickstart

```bash
pip install -e .
python examples/run_demo.py            # record a run
python examples/run_demo.py --replay   # replay it; assert identical decision + audit
```

## License

MIT (see LICENSE).
