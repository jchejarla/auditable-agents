# auditable-agents

A minimal, single-process layer that makes **LLM-agent decisions reproducible and
auditable** by applying four established distributed-systems techniques — **event
sourcing, idempotency, record-replay, and sagas** — to an agent workflow.

LLM agents are non-deterministic and usually leave no complete record of what they did,
which is hard to defend in regulated settings — finance especially — that require decisions
to be reconstructable and auditable. This is a small reference implementation of a pattern
that fixes that — not a production framework. It is demonstrated on a trade pre-approval
workflow, but the pattern is domain-agnostic.

> Reference prototype for the article *"Making AI Trading Decisions Auditable:
> Distributed-Systems Discipline for Agentic AI in Regulated Finance"* (in preparation).

## How it works

The agent is unchanged; every step it takes passes through a thin layer:

- **Event sourcing** — each step (tool call, model call, decision) is an immutable, ordered
  event. The event log *is* the audit trail.
- **Record-replay** — the model and tool calls are recorded on the first run and replayed
  afterward, so any past run reproduces exactly. (It also means replay needs no model,
  network, or API budget.)
- **Idempotency** — each step runs at most once; a retried or resumed run reuses completed
  steps instead of repeating them.
- **Sagas** — a multi-step action that fails partway is rolled back via compensating steps,
  and the rollback is recorded in the audit trail too.

## Demo workflow

A mock **AI-assisted trade pre-approval**: an agent checks compliance rules and an exposure
limit, asks a model to decide APPROVE/REJECT with a rationale, then (on approval) reserves
buying power and submits the order. Three scenarios are shipped as example audit trails in
[`scenarios/`](scenarios): **approve**, **reject**, and **rollback** (submission fails and
the reservation is released).

## Quickstart

```bash
pip install -e ".[dev]"

python examples/run_demo.py            # record a run, print the audit trail
python examples/run_demo.py --replay   # replay it — identical decision + audit trail

python examples/run_scenarios.py       # regenerate the approve/reject/rollback trails
python examples/bench.py               # overhead of the layer vs a no-layer baseline
pytest                                 # determinism, exactly-once, divergence, saga state
```

## The model: stub by default, real LLM optional

The model is a plain callable, `(prompt, tool_results) -> {"decision", "rationale",
"confidence"}`, so the layer is model-agnostic.

- **Default:** an in-process stub (no dependencies, no cost). It draws a per-call confidence
  score, so its output genuinely **varies between calls** — which is what makes record-replay
  observable: two unguarded runs diverge, but a replayed run reproduces the recording exactly.
- **Real LLM:** pass your own callable via the `model=` argument. See
  [`examples/real_model.py`](examples/real_model.py) for a Claude example using structured
  outputs (`pip install anthropic`, set `ANTHROPIC_API_KEY`). Record-replay captures the
  model's output once, so even a stochastic model replays byte-for-byte.

## Reproducibility, demonstrated

`pytest` includes the property the whole approach rests on:

- `test_determinism.py` — a recorded run replays to a byte-identical decision and audit trail.
- `test_divergence.py` — two independent recordings of the same request **differ** (the model
  is stochastic), yet replaying either reproduces it exactly.
- `test_exactly_once.py` — a retried/resumed run re-executes nothing and adds no new events.
- `test_input_sensitivity.py` — a different request never reuses a prior request's decision.
- `test_saga_state.py` — approval reduces buying power; rollback restores it.

## Scope and limitations

Deliberately minimal: single process, an append-only JSON-lines event log, deterministic
tools, and a stub model by default. It demonstrates the *pattern*, not a production system.
Notably, a real deployment would need: durable/replicated storage (the log here uses buffered
file writes, no `fsync`); atomic recording of a side effect with its event (here the side
effect runs just before its event is appended); and a retention/compaction policy for the
log. These are discussed in the article.

## Layout

```
src/auditable_agents/
  event_store.py    # append-only event log (source of truth + audit trail)
  record_replay.py  # record once, replay/reuse afterward (the determinism core)
  runner.py         # durable step runner: idempotent, exactly-once
  saga.py           # compensation / rollback for multi-step actions
  audit.py          # render a human-readable audit trail from the log
  agent.py          # the model-reasoning step (stub model + pluggable real model)
  workflow.py       # the mock trade-pre-approval workflow
examples/  run_demo.py  run_scenarios.py  bench.py  real_model.py
tests/     test_determinism.py  test_exactly_once.py  test_divergence.py
           test_input_sensitivity.py  test_saga_state.py
scenarios/ approve.audit.txt  reject.audit.txt  rollback.audit.txt
```

## License

MIT (see [LICENSE](LICENSE)).
