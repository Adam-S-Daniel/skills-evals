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
  run_canary.py            # runner: probes the guidance-bridge canary against the real CLI
  scorers/
    objective.py           # scriptable assertions on the output workspace
    judge.py               # LLM-as-judge rubric scoring
evals/
  pin-actions-to-sha/      # first reference eval
    fixture.yaml           # prompt, arms, objective checks, judge rubric
    seed/                  # workspace the agent starts from (unpinned workflows)
  guidance-bridge-canary/  # behavioral canary for the CLAUDE.md -> @AGENTS.md import
    fixture.yaml           # prompt, disallowed tools, per-layout magic tokens
    layouts/               # bridge / no-bridge / fence probe workspaces
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
at a checkout of the `agentskills` registry — the `with_skill` arm resolves
the skill dir by globbing `plugins/*/skills/<skill>` (the first sorted match
wins), so it works whether the registry lays a skill out under a plugin
named after that skill (`plugins/<skill>/skills/<skill>/`, legacy) or under a
bundle plugin holding several skills (`plugins/<bundle>/skills/<skill>/`).
It then copies that resolved directory (the one containing `SKILL.md`) into
the workspace's `.claude/skills/<skill>/`.

## Guidance-bridge canary

The fleet's agent guidance lives in each repo's `AGENTS.md`; `CLAUDE.md`
carries just an `@AGENTS.md` import line that Claude Code's memory loader
expands. That loader's import behavior has changed upstream more than once,
so a repo can silently lose all its guidance while its CLAUDE.md still looks
correct — only a behavioral probe, actually asking an agent whether guidance
made it into context, proves the bridge still works. Implements
[skills-evals#5](https://github.com/Adam-S-Daniel/skills-evals/issues/5),
item 3 of
[Adam-S-Daniel/_agent-guidance#17](https://github.com/Adam-S-Daniel/_agent-guidance/issues/17).

Run it:

```bash
python3 harness/run_canary.py evals/guidance-bridge-canary
```

Add `--subagent` to also probe subagent memory passing (a Task-launched
subagent asked the same question against the bridge layout):

```bash
python3 harness/run_canary.py evals/guidance-bridge-canary --subagent
```

This needs real API access — like a full eval run, it is **not** part of the
hermetic test suite (`test/run_tests.py` exercises this runner against
`test/fake-claude` only) and is **not** run in CI. Run it on demand, or wire
it into a schedule. Each run's report records `claude --version`, so a
regression can be tied to a specific CLI release.

### What a failure means

- **`bridge` failed** (magic word expected but absent) — likely a CLI import
  regression: check anthropics/claude-code#7768, #18371, #18518, #24987,
  #29525 for the historical pattern, and the CLI changelog for the version
  recorded in the report. Could also be fixture rot — check
  `layouts/*/CLAUDE.md` and the tokens in `fixture.yaml` haven't drifted.
- **`no-bridge` or `fence` failed** (magic word visible but shouldn't be) —
  either the probe's tool controls broke (foraging leaked the token) or
  native AGENTS.md support arrived
  ([anthropics/claude-code#6235](https://github.com/anthropics/claude-code/issues/6235))
  — a signal to simplify the fleet's guidance-bridge pattern, not a fleet
  failure.
- **`bridge-subagent` failed** — subagent memory passing regressed.

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
- [x] Guidance-bridge canary (`harness/run_canary.py`)
- [ ] Regression tracking (compare a run against the previous one)
