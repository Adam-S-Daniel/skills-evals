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
    `workflow-path-audit`: replay a changeset through each workflow's `on:`
    filters and assert exactly which workflows fire, and that they parse).
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

## Reference eval: `workflow-path-audit`

The first reference eval targeted a different skill, one since retired from the
registry — its rule moved into always-on managed guidance instead. The A/B
instrument was retargeted rather than retired: same harness, same fixture
schema, a surviving skill as the subject. `workflow-path-audit` was chosen
because, like its predecessor, it acts on `.github/workflows/` and its outcome
is objectively decidable from the resulting files alone.

- **seed** — a service repo whose five workflows carry no path filters at all:
  a required-check test workflow, a docs-site build, a deploy, a nightly
  schedule-only sweep, and an issue-driven triage. Plus the branch-protection
  ruleset (`.github/rulesets/main.json`) naming which check is required.
- **prompt** — "Make each workflow trigger only when a file it actually
  depends on has changed."
- **objective check** — replay four changesets (docs-only, source-only,
  lockfile-only, prose-only) through each workflow's `on:` filters using
  GitHub's own path-matching semantics, and assert exactly which workflows
  fire; the workflow carrying a required status check must have no
  workflow-level filter and must gate its real work on a computed salience
  output instead; every workflow still parses; the schedule/issue-only
  workflows and the ruleset are untouched.
- **judge rubric** — were all workflows covered, are the listed paths the ones
  each workflow's own steps actually consume, and did it leave alone what it
  should have? (Routing is verified objectively rather than judged — the four
  probe changesets sample it exactly, where a tool-less judge could only
  guess.)
- **expected result** — the `with_skill` arm materially outperforms baseline on
  completeness, and specifically on the required-check trap: a workflow-level
  filter on a required check leaves it missing and deadlocks the merge, which
  is the non-obvious thing the skill carries.

## Open decisions (defaults proposed — confirm or override)

- **Harness language:** Python — CHOSEN and implemented for the objective scorer.
- **Agent under test:** CHOSEN and implemented — the Claude Code CLI, invoked
  headlessly per arm:
  `claude -p <prompt> --output-format json --permission-mode bypassPermissions
  --setting-sources project` (plus `--model <model>` if the fixture or CLI
  flag sets one). The binary is `$CLAUDE_BIN` if set, else `claude` on `PATH`,
  so tests can substitute a fake CLI. `--setting-sources project` scopes skill
  discovery to the workspace's own `.claude/`, which is what makes the
  with_skill/without_skill split possible in the same environment.
- **Judge model:** CHOSEN and implemented — a second, independent headless
  `claude -p ... --output-format json` call. Its prompt embeds the fixture's
  rubric, the agent transcript, and the workspace diff (`git diff --cached`,
  with `.claude/` excluded — see below), and demands a JSON-only response of
  `{"dimensions": [...], "overall": ...}`. **Known limitation:** the Claude
  Code CLI has no flag to set sampling temperature, so the judge runs at
  whatever the CLI's default is — not the temperature-0 originally proposed
  here. Flagging this rather than silently dropping the requirement.
- **Cost capture:** CHOSEN and implemented — from the CLI's `--output-format
  json` payload: `total_cost_usd`, `usage`, `num_turns`, `duration_ms`.
- **What's committed:** fixtures + summarized reports; raw transcripts
  gitignored.

### Skill install path (corrected)

Claude Code auto-loads a skill from `.claude/skills/<name>/` only when
`SKILL.md` sits directly at that path. In the `agentskills` registry, each
skill ships as part of a *plugin*, with the actual skill content nested one
level deeper:

```
plugins/<plugin>/.claude-plugin/plugin.json
plugins/<plugin>/skills/<skill>/SKILL.md   <- this is what gets installed
```

The registry has shipped (and, mid-migration, may still contain a mix of)
two layouts for `<plugin>`:

- **Legacy, one skill per plugin:** `<plugin> == <skill>` — a plugin dir
  named after its single skill, e.g. `plugins/writing-adrs/skills/writing-adrs/`.
- **Bundle, many skills per plugin:** `<plugin>` is a bundle name distinct
  from any skill it contains, e.g. `plugins/adam/skills/workflow-path-audit/`
  alongside other skills under that same `adam` bundle.

Because the plugin/bundle directory name can't be assumed to equal the skill
name — and because cms-platform's flat `skills/<skill>/` and adamdaniel.ai's
`.claude/skills/<skill>/` shapes need the same treatment (issue #63) —
resolution is not a glob hardcoded in `run_agent` any more. Each registry
gets a `layout` glob in [`harness/registries.yml`](harness/registries.yml)
(`plugins/*/skills/*/SKILL.md` for agentskills, `skills/*/SKILL.md` for
cms-platform, `.claude/skills/*/SKILL.md` for adamdaniel.ai), and `run_agent`
substitutes the skill name for the placeholder segment immediately before
`SKILL.md`. It globs for the `SKILL.md` FILE itself, not the containing
directory, and takes that file's parent — so a skill directory that exists
but has no `SKILL.md` inside it (a stub left by a rename, a bundle
mid-migration) fails closed as `skill_not_found` rather than "installing"
whatever's actually in there. Matches are sorted and the first is used, so
resolution is deterministic even if a skill name were ever (mistakenly)
present under more than one plugin/bundle. The `with_skill` arm then copies
that resolved directory to `<workspace>/.claude/skills/<skill>/` — copying
the outer plugin/bundle directory instead would silently produce a workspace
where the skill never loads. `run_agent` fails loudly, naming the glob
pattern searched, if nothing matches.

## Scaling to the registry (2026-08-30)

One eval exists; the other ~30 registry skills have none. This section is the
method for closing that gap without a big-bang project: classify each skill to
the right instrument, mine fixtures from the incident record instead of
inventing tasks, and let process gates accrue coverage where the churn is.
The scale target is deliberately small — validation-gated skill iteration
(WikiSkill, arXiv:2608.27454) ran on 10–40-task validation splits, so per
skill here a handful of fixtures is in-spec, not a compromise.

### Four instruments, one harness

Not every skill takes the same eval, and some take none. Classify first:

- **A. Workspace transforms** — correctness is decidable from the resulting
  files alone. The `workflow-path-audit` shape applies unchanged: seed +
  objective checks + thin judge. Candidates: `review-bash-ci-reliability`,
  `code-quality`, `post-failure-comment`, `admin-config-render`,
  `writing-adrs` (the format half), `rename-pdfs`, `pdf-ocr-audit`.
  (`github-actions-sha-pinning` was also Class A; it has already shipped —
  see "Backfill order" below.)
- **B. Diagnosis/triage** — correctness = reaching a recorded root cause.
  The hermetic trick is a fake `gh` on the seed workspace's `PATH` serving
  canned JSON captured from the real incident (the same substitution move as
  `$CLAUDE_BIN`/`test/fake-claude`, applied to the tool the skill consults).
  The verdict is scored objectively against the postmortem; the judge grades
  reasoning quality only. Candidates: `cms-stuck-pr-triage`,
  `debug-github-workflows`, `ci-watcher-loops`, `editorial-label-audit`,
  `skills-doctor`, `consumer-repo-provisioning` (the
  which-secret-is-missing half).
- **C. Judgment/style** — the judge carries the load; keep the few decidable
  bits objective (banned buzzwords absent, required sections present), and
  prefer pairwise preference against committed reference samples over
  absolute rubric scores. Expect noise; run more trials. Candidates:
  `adam-writing-style`, `finding-unknowns`.
- **D. Wrong instrument entirely** — record the decision in the
  non-coverage table below instead of leaving a silent gap.

Reference-heavy skills (`aws-bootstrap`, `preview-environments`, and
`consumer-repo-provisioning`'s tables) fail by going stale, not by teaching a
bad procedure. Their instrument is a **freshness lint in the registry's own
CI** — every file, workflow, and secret name a SKILL.md cites still exists
where it points — not an A/B rollout here.

### Fixtures are mined, not invented

The fleet's incident record is a pre-scored task set: every dated incident in
the fleet guidance, every root-cause writeup in cms-platform's
`docs/VERSION-HISTORY.md`, every postmortem issue. Per fixture:

1. **Seed** — reconstruct the minimal pre-incident workspace. Scrub it:
   `example.com`/`example.net` only, no real addresses — this repo is public
   and fixtures are committed.
2. **Prompt** — what the operator actually asked at the time.
3. **Objective check** — the recorded root cause or fix shape.

The expected A/B delta comes free: a real agent already missed this once, so
the ceiling-effect risk is pre-tested, and `with_skill` catching what the
baseline plausibly misses is exactly the delta the skill exists to buy.

### Harness-wide rules (promoted from the first fixture)

The `workflow-path-audit` fixture learned these the hard way; they are policy
for every fixture, not folklore in one file's comments:

- **Arms on a pinned mid-tier model, judge pinned strong.** A ceiling-effect
  arm is signal-free.
- **Anything a script can decide is never left to the judge**, and the
  rubric caps a dimension when a decidable fact fails (the judge once scored
  a 9 on an arm the objective column failed).
- **Correctness outweighs guardrails** in judge weights — equal-weighted
  restraint quietly rewards the do-nothing arm.
- **3–8 small fixtures per skill beat one big one.** Coverage definition:
  every claim in the skill's body has at least one fixture that would fail
  without it.
- **N≥3 trials per arm before believing a delta**, and reports carry the
  trial count. The CLI has no temperature flag (see Open decisions), so
  trials are the mitigation.
- **Hermetic, always** — no network, no wall-clock; canned payloads and fake
  binaries.
  A fixture puts a fake binary in front of the real one with an `env:`
  block (`PATH: "$WORKSPACE/bin:$PATH"`; `$WORKSPACE` expands to the arm's
  temp workspace), and reads what the agent did off the log the fake writes
  — `file_matches` over the log, `transcript_matches` over the final reply.
  `windows-elevation-from-wsl` is the first fixture in that shape.

### Coverage accrues by process, not by project

- **Graduation gate:** a skill enters the registry with at least one fixture
  here, and the graduation PR's definition of done includes a green
  `with_skill` run.
- **Touch gate:** a PR that edits an existing SKILL.md either runs that
  skill's eval or adds its first fixture.

Both gates belong in the registry's own contributor guidance (agentskills'
`AGENTS.md` repo-specific additions and the skill-creator flow); this file is
the reference they point at.

Backfill order, by usage × decidability × incident material:
`review-bash-ci-reliability` (the incident record practically is its fixture
set), `cms-stuck-pr-triage` (builds the fake-`gh` machinery every Class B eval
reuses), `debug-github-workflows`, then `adam-writing-style` as the Class C
pilot. (`github-actions-sha-pinning` — fully decidable, including the
cms-platform tag carve-out — has shipped: `evals/github-actions-sha-pinning/`.)

### Deliberate non-coverage

A row here is a decision with a reason; an absent eval without a row is a
gap. (Mirrors the fleet convention that "deliberately out" and "not adopted
yet" must stay distinguishable.)

| Skill | Decision | Reason |
|---|---|---|
| `test-canary` | no A/B | delivery probe; covered by the propagation arms |
| `sveltia-cms-playwright-demo` | skip | historical reference to retired tech |
| `wj-next-break` | skip | wall-clock/calendar-bound; low value to freeze |
| `launch-wsl-claude-session`, `sync-skills`, `sync-cc-settings-between-wsl-and-windows`, `migrate-claude-memory`, `compare-pdfpairs`, `ocr-pdfs` | defer | machine-bound (WSL/WPF/browser surfaces); faking the surface costs more than the churn justifies today |
| `windows-elevation-from-wsl` | Class B, covered | the one machine-bound skill whose surface is cheap to fake: `evals/windows-elevation-from-wsl/seed/bin/powershell.exe` answers reads, denies writes, refuses dodges, and logs; the fixture's `env:` block puts it on the arm's `PATH` |
| `fastmail` bundle | defer | credentialed live service; a fixture may not carry real accounts, and a faked Fastmail is a harness project of its own |
| `aws-bootstrap`, `preview-environments` | freshness lint | staleness is the failure mode, not procedure quality |

### Budget

Do not grow the weekly matrix linearly with coverage. Evals run on-touch (PR
path filters over `evals/<skill>/**` and the skill's own registry path); the
scheduled lane runs a rotating subset weekly or the full sweep monthly.
`eval.yml` itself gets salient-path filters — the `workflow-path-audit`
doctrine applies to the harness's own CI.

### `claude plugin eval` (assessed 2026-08-30)

The CLI's native eval harness was assessed against this design. It has
first-class with/without-baseline arms and a stable `aggregate-result.json`
report, but: it is early-access and gated for this account (probing prints
"currently in early access"); its graders are regex / tool-use / file-exists
/ LLM-judge / baseline only, with **no scriptable grader**, so it cannot host
`scorers/objective.py`'s changeset replays — which would force decidable
facts back onto regex or the judge, the exact anti-pattern the rules above
forbid; and its case layout is per-plugin where this harness is centralized.

Decision: **monitor, don't wrap.** Re-evaluate when it is both un-gated for
this account and has grown a run-a-script grader; until then this harness
stays the system of record. If `results/` is ever restructured, mirror its
report schema to keep a future migration cheap.

## Out of scope

- `GHA-bench` as the harness (#18 caveat) — this is a dedicated harness.
