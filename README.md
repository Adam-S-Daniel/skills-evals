# skills-evals

Evals for the [`agentskills`](https://github.com/Adam-S-Daniel/agentskills)
registry: for each skill, measure agent quality **with vs. without** the skill
installed, so "this skill helps" is a number instead of an assertion.

Implements Phase 5 of
[agentskills#18](https://github.com/Adam-S-Daniel/agentskills/issues/18).
Full method and rationale: [`DESIGN.md`](DESIGN.md). Deliberately a dedicated
harness — `GHA-bench` is not used for this.

## Layout

```
DESIGN.md                  # eval method, harness shape, open decisions
harness/
  run_eval.py              # runner: loads a fixture, runs both arms, scores, reports
  scorers/
    objective.py           # scriptable assertions on the output workspace
    judge.py               # LLM-as-judge rubric scoring (stub — see DESIGN.md)
evals/
  pin-actions-to-sha/      # first reference eval
    fixture.yaml           # prompt, arms, objective checks, judge rubric
    seed/                  # workspace the agent starts from (unpinned workflows)
results/                   # run summaries (raw transcripts are gitignored)
```

## Running

```bash
python3 harness/run_eval.py evals/pin-actions-to-sha --arm objective-only
```

The runner currently implements fixture loading, workspace setup, and the
objective scorer end-to-end. Agent invocation (spawning Claude Code on the seed
workspace per arm) and the LLM judge are clean stubs — the interfaces and the
fixture schema are settled; see `DESIGN.md` §Open decisions before wiring them.

## Status

- [x] Design (`DESIGN.md`)
- [x] Fixture schema + first fixture (`pin-actions-to-sha`)
- [x] Objective scorer (real, tested against the seed)
- [ ] Agent invocation (both arms)
- [ ] LLM-as-judge scorer
- [ ] Report generation + regression tracking
