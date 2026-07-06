# skills-evals — design

Evals for the [`agentskills`](https://github.com/Adam-S-Daniel/agentskills)
registry. Implements Phase 5 of
[agentskills#18](https://github.com/Adam-S-Daniel/agentskills/issues/18).

## Purpose

Answer, per skill: **does installing this skill actually improve agent
behavior?** The core method is an A/B: run the same task **with** the skill
installed vs. **without**, score both arms, and report the delta.

This is purpose-built for registry skills. Per the #18 caveat, `GHA-bench` is
**not** used as the harness.

## What we measure (per skill)

- **Task success** — scriptable, objective assertions on the result.
- **Quality** — an LLM-as-judge rubric (correctness, completeness, adherence to
  the skill's stated intent), returning scores + rationale.
- **Cost** — tokens, wall-clock, tool-call count.
- **Regression** — track the with/without deltas over time per skill.

## Harness shape

- **Fixtures** — each skill gets `evals/<skill>/` with one or more task
  fixtures: a prompt + a seed workspace (input files) + expected-outcome checks
  + a judge rubric.
- **Arms** — `with_skill` (skill installed via marketplace or a local
  `plugins/<name>/` path) and `without_skill` (baseline, same prompt).
- **Runner** — invokes the agent (Claude Code / Agent SDK) on the fixture in an
  isolated workspace, captures the transcript, the resulting files, and token
  usage.
- **Scorers**
  - *objective* — assertions on output files / exit state (e.g. for
    `pin-actions-to-sha`: every `uses:` is a 40-hex SHA with a version comment
    and the workflow still parses).
  - *judge* — an LLM grades the transcript/result against the fixture's rubric,
    emitting JSON (scores + reasons), temperature 0.
- **Report** — per-skill table of with vs. without across success %, judge
  score, and cost; a summary; and a regression line vs. the last run.

## Directory layout

```
skills-evals/
  README.md
  DESIGN.md                # this file
  harness/                 # runner + scorers (Python)
    run_eval.py
    scorers/
      objective.py
      judge.py
  evals/
    <skill>/
      fixture.yaml         # prompt, seed ref, objective checks, judge rubric
      seed/                # input workspace the agent starts from
  results/                 # summaries committed; raw transcripts gitignored
```

## How it pulls skills

Two modes:
1. **Marketplace install** (`/plugin install <skill>@agentskills`) — realistic,
   tests the shipped artifact.
2. **Local path** — point at a `plugins/<name>/` checkout to eval a skill
   *before* it merges into the registry.

## First reference eval (proposed): `pin-actions-to-sha`

- **seed** — a repo with `.github/workflows/*.yml` using tag refs
  (`actions/checkout@v4`, etc.).
- **prompt** — "Pin all GitHub Actions to full commit SHAs."
- **objective check** — every `uses:` becomes a 40-hex SHA followed by a
  `# vX.Y.Z` version comment; non-action `uses:` (local/Docker) left alone;
  every workflow still parses.
- **judge rubric** — did it pin *all* refs, preserve the version in a comment,
  avoid touching things it shouldn't, and explain what it did?
- **expected result** — the `with_skill` arm materially outperforms baseline on
  completeness/correctness.

## Open decisions (defaults proposed — confirm or override)

- **Harness language:** Python — CHOSEN and implemented for the objective scorer.
- **Agent under test:** Claude Code / Agent SDK; model matrix configurable,
  default a current Claude model.
- **Judge model:** a current Claude model, temperature 0, JSON-schema'd output.
- **Cost capture:** from the SDK usage payload.
- **What's committed:** fixtures + summarized reports; raw transcripts
  gitignored.

## Out of scope

- `GHA-bench` as the harness (#18 caveat) — this is a dedicated harness.
- `civic-platform-agents` (#18 caveat).
