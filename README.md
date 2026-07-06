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
    judge.py               # LLM-as-judge rubric scoring
evals/
  pin-actions-to-sha/      # first reference eval
    fixture.yaml           # prompt, arms, objective checks, judge rubric
    seed/                  # workspace the agent starts from (unpinned workflows)
results/                   # run summaries (raw transcripts are gitignored)
test/
  run_tests.py             # harness's own test suite (hermetic, no real `claude`)
  fake-claude              # stand-in CLI used by the tests
```

## Running

Objective-only (no agent invocation — scores a workspace as-is):

```bash
python3 harness/run_eval.py evals/pin-actions-to-sha --arm objective-only
```

Full A/B run (spawns the Claude Code CLI headlessly for each arm, scores with
the objective checks and the LLM judge, writes `results/<skill>/<timestamp>/`):

```bash
python3 harness/run_eval.py evals/pin-actions-to-sha --arm both \
  --registry ~/repos/agentskills
```

Useful variations:

```bash
# Only the with_skill or without_skill arm:
python3 harness/run_eval.py evals/pin-actions-to-sha --arm with_skill --registry ~/repos/agentskills

# Skip the LLM judge (objective checks + cost/turns only):
python3 harness/run_eval.py evals/pin-actions-to-sha --arm both --no-judge

# Point at a different agent binary, registry checkout, or output root:
CLAUDE_BIN=/path/to/claude AGENTSKILLS_DIR=~/repos/agentskills \
  python3 harness/run_eval.py evals/pin-actions-to-sha --arm both --results-dir /tmp/eval-out
```

`--registry` (else `$AGENTSKILLS_DIR`, else `~/repos/agentskills`) must point
at a checkout of the `agentskills` registry — the `with_skill` arm installs
the skill by copying `plugins/<skill>/skills/<skill>/` (the directory
containing `SKILL.md`) into the workspace's `.claude/skills/<skill>/`.

## Tests

The harness has its own hermetic test suite — no real `claude` binary is ever
invoked; a fake CLI (`test/fake-claude`) stands in for it:

```bash
python3 test/run_tests.py
```

This is what CI (`.github/workflows/ci.yml`) runs.

## Status

- [x] Design (`DESIGN.md`)
- [x] Fixture schema + first fixture (`pin-actions-to-sha`)
- [x] Objective scorer (real, tested against the seed)
- [x] Agent invocation (both arms)
- [x] LLM-as-judge scorer
- [x] Report generation
- [ ] Regression tracking (compare a run against the previous one)
