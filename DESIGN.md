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
    guidance.py            # guidance subject: payload assembly, delivery, guard
    registries.yml         # registry name -> URL -> skill-directory layout
    scorers/
      objective.py
      judge.py
    fakes/                 # stand-in binaries shared across Class B fixtures
      gh                   # offline GitHub CLI (see "Four instruments", B)
      README.md            # its keying rule, classes, and invocation log
  evals/
    <skill>/
      fixture.yaml         # prompt, seed ref, objective checks, judge rubric
      seed/                # input workspace the agent starts from
      seed/bin/<tool>      # symlink to ../../../../harness/fakes/<tool>, for
                           # a fixture whose `env:` puts it first on PATH
    guidance/<section id>/ # subject: guidance — a section, not a skill
      fixture.yaml         # section id, arms + delivery modes, checks, rubric
  results/                 # summaries committed; raw transcripts gitignored
    <skill>/<timestamp>/<arm>/summary.json
    guidance/<id>/<timestamp>/<arm>/summary.json
```

## Fixture schema: `fixture.yaml`

Fields a fixture may set, beyond the ones the reference eval below already
shows (`skill`, `registry`, `model`, `judge`, `prompt`, `arms`,
`objective_checks`, `judge_rubric`, `env`, `timeout_s`):

- **`setup:`** (optional) — a shell command, run once in the workspace
  before anything else touches it: before the agent (`with_skill`/
  `without_skill`/`both`), and before objective-only scoring of a freshly
  copied seed (`--arm objective-only` without an explicit `--workspace`).
  Runs with `cwd` set to the workspace and `$WORKSPACE` (plus any other
  `$VAR`) expanded the same way `env:` values are — `setup: "bash
  $WORKSPACE/setup.sh"` and a bare `setup: "bash setup.sh"` are
  equivalent, since `cwd` is already the workspace.

  Use it when a seed can't hold its target state as literal checked-in
  files — the motivating case is a fixture that needs one or more real git
  repositories present in the workspace: committing a built repo (complete
  with its own `.git/`) as literal seed files would make it an *embedded*
  repository from the harness's own bookkeeping commit's point of view
  (`git add -A` treats a nested `.git` as a submodule boundary, not plain
  files to add). `evals/disarm-inherited-reach/seed/setup.sh` builds a bare
  "production" repository, a real clone of it, and a linked worktree this
  way, with a fixed author/committer identity and
  `GIT_AUTHOR_DATE`/`GIT_COMMITTER_DATE` so every SHA it produces is
  reproducible — which is what lets an objective check compare against a
  *snapshot* of the SHAs `setup:` itself produced (`git_ref_unchanged`'s
  `snapshot:` form, below) rather than a SHA hardcoded in `fixture.yaml`,
  which would go stale the moment `setup.sh`'s own output changed for an
  unrelated reason. A `setup:` script that no longer needs its own template
  files after it runs should delete them (and itself) as its last step, so
  the agent's workspace shows only the built state, not the machinery that
  built it.

  An explicitly given `--workspace` is scored as-is; `setup:` is the
  caller's own responsibility there; it is not re-run automatically. A
  nonzero exit (or a `setup_timeout_s:`-bounded timeout, default 60s)
  fails the whole arm/run with a named `setup_failed` error carrying the
  captured stderr/stdout — never a bare traceback out of a check that
  assumed the setup had already put its files in place — and the agent is
  never invoked.

### Git-state objective check types (`harness/scorers/objective.py`)

Added for fixtures whose target state is one or more real git repositories
(see `setup:` above) — decided by asking git, or by walking the
filesystem, never by matching a regex over a diff or a config file's raw
text:

- **`git_ref_unchanged`** — a named ref in a workspace-relative repo still
  resolves to the expected SHA. Either `expected:` (a SHA fixed at
  fixture-authoring time) or `snapshot:` (a workspace-relative JSON file —
  `{"<path>": {"<ref>": "<sha>"}, ...}` — a hermetic `setup:` script writes
  alongside the state it built, read at check time instead of a SHA baked
  into `fixture.yaml`).
- **`git_remote_url_is`** — `git -C <path> remote get-url <remote>` names
  the expected path. Survives a `git remote rename` that a `file_matches`
  regex over `.git/config` would not (the URL line is untouched, only the
  section name changed).
- **`no_git_config_names_path`** — no git-dir `config` file anywhere under
  the workspace — `.git/config`, a bare repo's `<name>.git/config`, or a
  submodule's `.git/modules/<name>/config` (an `exclude:` list of top-level
  dirs is skipped entirely) — names a forbidden path. Scoped to the
  workspace by design: a copy made outside it is invisible here,
  deliberately (see the judge rubric instead).
- **`reaper_ran_in_standalone_repo`** — every directory a destructive
  script logged running in was, at that moment, a standalone repository
  (not a linked worktree) with no remotes left — decided from live
  inspection when the directory still exists, falling back to facts the
  script itself recorded (its own `git rev-parse --git-dir` and `git
  remote` output) once it's gone.
- **`reaper_avoided_paths`** — none of those same logged directories IS
  (path identity, not a regex over the logged text) one of a list of
  forbidden workspace-relative paths.
- **`git_worktree_list_matches`** — `git worktree list` on a path names
  exactly the expected set, each compared as a path relative to the
  workspace (not by basename — a relocated worktree can share a removed
  one's basename).

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
  objective checks + thin judge. Candidates: `code-quality`,
  `admin-config-render`, `pdf-ocr-audit`.
  (`github-actions-sha-pinning` was also Class A; it has already shipped —
  see "Backfill order" below.) `rename-pdfs` graduated out of this list:
  covered by `evals/rename-pdfs/` (issue #82). `post-failure-comment`
  graduated out of this list: covered by `evals/post-failure-comment/`
  (issue #86). `writing-adrs` graduated out of this list: covered by
  `evals/writing-adrs/` (issue #80). `review-bash-ci-reliability` graduated
  out of this list: covered by `evals/review-bash-ci-reliability/` (issue #74).
- **B. Diagnosis/triage** — correctness = reaching a recorded root cause.
  The hermetic trick is a fake `gh` on the seed workspace's `PATH` serving
  canned JSON captured from the real incident (the same substitution move as
  `$CLAUDE_BIN`/`test/fake-claude`, applied to the tool the skill consults).
  The verdict is scored objectively against the postmortem; the judge grades
  reasoning quality only. `cms-stuck-pr-triage` graduated out of this list:
  covered by `evals/cms-stuck-pr-triage/` (issue #84), which is also where
  the shared `harness/fakes/gh` every other Class B fixture reuses came
  from. Candidates: `debug-github-workflows`, `ci-watcher-loops`,
  `editorial-label-audit`, `skills-doctor`, `consumer-repo-provisioning`
  (the which-secret-is-missing half).
- **C. Judgment/style** — the judge carries the load; keep the few decidable
  bits objective (banned buzzwords absent, required sections present), and
  prefer pairwise preference against committed reference samples over
  absolute rubric scores. Expect noise; run more trials. Candidates:
  `adam-writing-style`, `finding-unknowns`.

  A Class C fixture says so in its `judge:` block: `mode: pairwise` plus
  `references:` ({name, path} entries, relative to the fixture dir — a path
  that climbs out of it is refused, because a yardstick from elsewhere on
  the machine is neither reviewable nor reproducible). The judge is shown
  the writing under test beside those references, blind: every draft is
  normalised to the same line shape (a hard-wrapped reference beside an
  unwrapped reply is separable without reading a word), fenced with a
  per-call nonce so nothing inside a draft can pose as the prompt, and
  shuffled systematically per trial so no draft keeps a slot. The score IS
  the rank, 1 = best; `weights:` is an absolute-mode idea and is rejected
  here rather than half-honoured. `timeout_s:` (default 120) bounds the
  call, and a timeout is recorded as a judge error, never as a score.
  `harness/scorers/judge.py` documents the returned shape.
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
  block (`PATH: "$WORKSPACE/bin:$PATH"` — `${WORKSPACE}` reads the same;
  `$WORKSPACE` expands to the arm's temp workspace), and reads what the
  agent did off the log the fake writes — `file_matches` over the log,
  `transcript_matches` over the final reply.
  `windows-elevation-from-wsl` is the first fixture in that shape;
  `cms-stuck-pr-triage` is the second, and its `gh` is shared from
  `harness/fakes/`.
- **A check whose evidence is a log says so** (`require_present: true` on
  `file_matches`). A `must_not_match` over a file that does not exist
  PASSES, so "the agent attempted no write" is otherwise indistinguishable
  from "the agent never ran the tool", and deleting the log becomes a way
  to score restraint.

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
`cms-stuck-pr-triage` (builds the fake-`gh` machinery every Class B eval
reuses), `debug-github-workflows`, then `adam-writing-style` as the Class C
pilot. (`github-actions-sha-pinning` — fully decidable, including the
cms-platform tag carve-out — has shipped: `evals/github-actions-sha-pinning/`.
`review-bash-ci-reliability`, which headed this list because the incident
record practically is its fixture set, has shipped too:
`evals/review-bash-ci-reliability/`.)

### Deliberate non-coverage

A row here is a decision with a reason; an absent eval without a row is a
gap. (Mirrors the fleet convention that "deliberately out" and "not adopted
yet" must stay distinguishable.)

| Skill | Decision | Reason |
|---|---|---|
| `test-canary` | no A/B | delivery probe; covered by the propagation arms |
| `sveltia-cms-playwright-demo` | skip | historical reference to retired tech |
| `wj-next-break` | skip | wall-clock/calendar-bound; low value to freeze |
| `launch-top-level-claude-session` (renamed from `launch-wsl-claude-session` on 2026-09-25, [adam-agentskills PR 27](https://github.com/Adam-S-Daniel/adam-agentskills/pull/27)), `sync-skills`, `sync-cc-settings-between-wsl-and-windows`, `migrate-claude-memory`, `compare-pdfpairs`, `ocr-pdfs` | defer | machine-bound (WSL/WPF/browser surfaces); faking the surface costs more than the churn justifies today |
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

## Model roster (2026-09-04, #67; redesigned 2026-09-13, #147)

The harness's model choices were literals: an arm pinned in each fixture, a
judge beside it, a preflight model in `eval.yml`. Nothing in the repo noticed
when a model shipped or retired, and the first symptom would have been a run
against a model that no longer exists.

**The roster the harness RUNS ON is `evals/roster.yml`, committed on `main`.**
That is [ADR 0001](docs/decisions/0001-roster-trusted-on-main.md), and it is
the whole shape of the feature: `main` is ruleset-protected and pull-request
only, so an arm, the judge, the preflight model or a `catalogue_seen` entry
cannot appear there or vanish from there without a reviewed commit.
`run_eval.select_models` reads that file and nothing else for the roster rung
of its precedence (`--model` > the fixture's own pin > `evals/roster.yml` >
error).

**`harness/roster.py` computes a PROPOSAL, not the running set.** It is still
**a pure function over files** — already-parsed documents and a frozen `now`
in, a roster dict out; no network, no clock, no environment — which is what
makes the whole policy testable at the granularity of one threshold. The
single network call in the feature is `scripts/refresh_models.py`; the usage
side is `scripts/model_usage_census.py`, which runs on a durable machine (a CI
runner has no transcripts) as a best-effort passenger on the Tier-3
account-store Routine. Its output carries a `proposal` block —
`{status: "same"|"differs", changes: [...]}` — computed against the committed
file, with every seat change carrying its numerator, its denominator and the
share they make, in words.

**What each store is trusted for**, stated once because the previous design's
defects all came from leaving it unstated:

| Store | Trusted for | Written by |
| --- | --- | --- |
| `evals/roster.yml` (on `main`) | the running set, and the observation history (`catalogue_seen`) | a human, through a reviewed pull request |
| the Models API response | availability, within the run that fetched it | Anthropic |
| `usage/latest.json` (on `eval-results`) | **nothing.** It can shape a proposal and nothing else | a job on another machine |
| `roster/latest.json` (on `eval-results`) | nothing. An exhibit for the explorer, read by no decision | this workflow |

**The proposal flow.** When the computed roster differs from the committed one,
`eval.yml` renders it with `scripts/render_roster_yaml.py` and admits the
rendered file against the committed-roster contract. A valid proposal is pushed
as one commit on the bot-owned branch `roster/proposal` (recreated from `main`
every run — never a shared branch), with one tracking issue carrying the
rendered summary and compare link. An invalid proposal instead leaves the
branch and compare link untouched and creates or updates a “needs review”
tracking issue with its admission failures. The paid eval result is still
published from the committed roster. A human opens the pull request for a valid
proposal and merges it after CI. That is the fleet's sanctioned bot-write path;
nothing in CI writes `evals/roster.yml`. When the computed roster matches, the
tracking issue is closed.

**Who is an arm (2026-09-22, Adam's decision).** Two rules, the second
subordinate to the first. **(1) Usage seats:** every available model at or
above `arm_enter_usage_pct` of rankable, attributable census turns over
`arm_enter_window_weeks` is an arm, with its share in its reason. **(2)
Newest per QUALIFYING tier:** in a tier rule 1 already seated somebody in,
the newest available model past the cooling-off is an arm too, and its reason
says so in words, naming the qualifying share it rides on. A tier no model of
which clears the entry bar gets no arm from rule 2, however new its newest
model is; that model is listed under `excluded` saying exactly that.

Rule 2 used to read "newest in its tier" across every tier on the ladder.
That seated the newest haiku and the newest fable on a census showing the
fleet ran 6.3% and 3.0% of its turns on them — a four-arm roster, at four
arms' worth of spend per fixture, two of whose arms measured tiers nobody
uses. The ladder decides *capability order*; it was never evidence that a
tier is worth measuring, and the census already is.

**The no-census fallback is deliberately NOT restricted.** With no usable
usage there is no usage-qualified tier at all, and a roster must not be
empty — so wherever the enter window carries no usable evidence (any of
`_census_verdict`'s eight verdicts, or a fresh census whose enter window
alone fails one of the ranked-usage floors) rule 2 reverts to newest per tier
across every tier, with the existing degradation reasons. A usable census
that simply names no model at the entry bar is a different thing: that is
evidence, and it says no tier qualifies, so the only seats are previous arms
held over the exit bar — and with none, `main()` refuses to publish a roster
with no arms (rc 3) and the committed one stands. Rule 2 added no threshold
of its own: it reads rule 1's entry bar, and every number stays in
`evals/roster-policy.yml`.

Five properties are load-bearing and should survive any rework:

1. **No model id in the machinery.** Tier comes from the family word in a
   model's own id, matched against a ladder in `evals/roster-policy.yml`. A
   model that ships after this was written needs no edit anywhere.
   `evals/roster.yml` is the one DATA file admitted to that guard, for the
   same reason a fixture's own `model:` pin is.
2. **Every entry carries its reason in words**, and every degradation says
   which degradation it was — absent census, stale census, future-dated
   census, census present but empty over the window. A roster that falls back
   silently is indistinguishable from one that did not need to. A proposed
   change carries, in addition, the numerator and denominator its share was
   taken over: a percentage with no counts behind it is unfalsifiable from
   the outside.
3. **No evidence is not evidence.** Nothing proposes retiring an arm except
   leaving the Models API or measurably falling under the exit bar. A missing
   or stale census proposes nothing.
4. **Two previous-roster states, not three.** The published `previous_state`
   is `compared` or `none` (nothing to compare against). The third,
   `unavailable`, is gone: a committed roster that is present and unreadable
   is a defect in this repository rather than a fact about an unprotected
   branch, so `compute_roster` raises `TrustedRosterUnreadable`, `main()`
   exits 5, and nothing is published at all.
5. **A since-retired model counts by catalogue HISTORY, not id shape.** The
   roster carries `catalogue_seen`: every model id the Models API has been
   observed to list, with the date it was last seen. A model that has left
   the API but that this harness has actually observed before still counts in
   the usage denominator — real work that happened does not stop counting
   just because the model is gone. An earlier approach inferred this from the
   id's SHAPE instead; that was withdrawn because shape cannot distinguish a
   since-retired real model from a plausibly-named proxy alias, and it missed
   the pre-#67 legacy id shape entirely.

   An entry's `last_seen` is refreshed to today whenever the Models API
   actually returns that id, and the entry is dropped once `last_seen` is
   older than `catalogue_seen_max_age_days`. **That is the only way an entry
   leaves.** Both the exemptions that used to sit beside it, and both length
   caps, are deleted — see below.

   **Ageing out is not a repair.** It ends a plant's future effect, but it
   does not undo a retirement the plant already caused: a model whose
   measured share fabricated usage pushed under the exit bar is proposed
   for retirement, and once that proposal is merged the model is no longer
   a previous arm, so the exit bar no longer applies to it and a dozen
   turns a week never re-seats it. It returns by clearing the ENTRY bar, by
   being the newest in a tier that some model of ITS OWN clears the entry
   bar in, or by hand.

   **Migration.** `evals/roster.yml` was seeded by hand with an empty
   `catalogue_seen`, because the only history that existed lived on
   `eval-results` and that branch is not trusted to supply one. So the first
   run after ADR 0001 landed behaves exactly like a genuine first run — the
   same migration `catalogue_seen`'s own introduction made — and a model
   retired before this harness observes it directly is unattributable until
   a run sees it.

**What was deleted, and why it is named here rather than left beside the
redesign.** Every one of these existed to approximate a trusted history over
an untrusted `previous.json`, and each is deleted with the measurement that
shows it now decides nothing (ADR 0001, decision 4):

- **The anchored denominator, the retirement veto keyed on it, and the
  count-only notice beside it.** They measured how much of a window's
  denominator rested on the previous roster; with that roster reviewed and
  committed, the fraction measures how much of the usage belongs to models
  this repository has a merged record of, and a veto on it refuses precisely
  the honest case.
- **The fold-relation question the ageing rule asked, and BOTH ageing
  exemptions.** They existed to disbelieve a `last_seen` date, which a
  trusted record does not need.
- **Both 500-entry length caps, the 10,000-entry carry ceiling, the tiering
  they evicted by, and `_clean_previous_arms`' never-evict clause and
  two-list return.** They bounded an unbounded public input; that input is
  bounded by review now, and every remaining effect was on honest data.

ADR 0001's decision 4 names each of them by identifier. Nothing else in the
tree does, deliberately: a name that no longer resolves is a name a reader
will go looking for.

**What stays**, and it is the shorter list: schema validation of every
untrusted field with a named one-line skip, the census freshness window and
its degradation reasons, the `judge.is_arm` refusal (now also a lint over the
committed file, run by `ci.yml`), and a SIZE BOUND on the census document —
`CENSUS_MAX_KEYS` and `CENSUS_MAX_BYTES` — so the one input still written by
another machine cannot exhaust the runner.

Thresholds, and the reasoning behind the numbers, belong in an ADR —
[#73](https://github.com/Adam-S-Daniel/skills-evals/issues/73). See the
README's "Model roster" section for the precedence rule and the census's
public-output contract.
## Guidance subject (2026-09-05, skills-evals#97)

**What it measures.** A skill is loaded when it is invoked; a guidance section
is loaded in every session of every fleet repo. The question that decides
whether a section stays is therefore not "does it teach the behavior" but
"does the full guidance WITH it beat the full guidance WITHOUT it", by enough
to pay for its bytes. So a `subject: guidance` fixture names a `section:` (an
id from `_agent-guidance`'s `agents-md/eval-coverage.yml`, stable across
heading rewordings) and its arms carry a delivery `mode:`. Five exist:
`none` (the control: no guidance, but a DECOY token of its own — see the
guard below), `stub` (`agents-md/stub.md`, what a
repo carries inline), `section` (the section's extent — its `##` heading
through the line before the next `##`, `###` children included — with its
file's intro prepended), `full` (the whole delivered corpus: `base.md`, plus
the section's own file when it is an opt-in `sections/*.md`), and
`full-minus-section` (that corpus with the extent removed). The default pair
`section`/`none` asks whether the section teaches; the declared
`ablation: [full, full-minus-section]` pair asks what it is worth in situ,
including any lost-in-the-middle effect of a 56 KB file. Extents are located
with a real markdown parse (`markdown-it-py`, pinned exact) using the same
arithmetic as `_agent-guidance`'s own `scripts/check-guidance-coverage.js`, so
the manifest's `bytes` column and the delivered payload can never disagree; a
regex would end an extent on the `## ` inside one of `base.md`'s fenced
blocks.

**The delivery path.** The fleet does not import its guidance from a repo
file — `fleet-memory.sh` writes a marked block into user memory
(`$CLAUDE_CONFIG_DIR/CLAUDE.md`, default `~/.claude/CLAUDE.md`), read once per
session. An eval of the guidance therefore delivers the same way: a fresh
scratch dir per arm, `CLAUDE_CONFIG_DIR` pointing at it, and the *real* hook
run with `FLEET_GUIDANCE_PAYLOAD` — running the real hook rather than
imitating it is the point, since a harness that reimplements the delivery path
measures the imitation. Guidance arms invoke the CLI with
`--setting-sources user,project`; skill arms keep `project` and are otherwise
untouched. Whether the pinned CLI honours `CLAUDE_CONFIG_DIR` for *memory*
specifically has not been measured against a live CLI yet, so `--delivery
project` exists as the documented fallback (same hook, pointed at the
workspace, read as project memory) and every summary records which was used —
`delivery: user` or `delivery: project`. Either way the guard, not this
choice, decides whether an arm counts. The agent's environment is an
allowlist, not the ambient one: `PATH`, `HOME`, `TMPDIR`,
`CLAUDE_CONFIG_DIR`, every `ANTHROPIC_*` variable, and the fixture's own
`env:` — `harness/propagation/arms.py` measured 16 vs 35 loaded skills between
a scrubbed and an ambient environment, and an arm that inherits the operator's
own settings is not measuring the guidance.

**The contamination trap, and why a guard is not optional.** On any machine or
hosted session carrying the fleet hook, the real `~/.claude/CLAUDE.md` already
IS the guidance. A harness that does not isolate the config dir per arm
delivers to BOTH arms and reports a null delta that reads as "the guidance
does nothing" — the most expensive kind of wrong answer, because it looks like
a result. So every payload ends in `The magic word is <token>.` with a fresh
random token per run (an earlier run's token would let a stale real config dir
satisfy this run's guard), and every arm is probed for it before it may score
anything: one tool-free `run_canary.run_leg` call, with the canary's own
disallowed-tools list so the model cannot forage the token off disk, against
that arm's config dir and workspace, on the preflight model (the fixture's
`model:` pin today; the roster's `preflight` entry once skills-evals#67
lands).

The control gets a **decoy**: no guidance, but a second fresh token of its
own, delivered through the same hook into the same kind of scratch config dir.
Without it the control's guard was vacuous — `mode: none` delivered nothing,
so its probe could only ever answer "no magic word", which is also what it
answers when the arm IS contaminated. So the guard claims exactly this: a
treatment arm was delivered its payload and reads it; a control arm reads its
own scratch user memory (it reports its decoy) and was not delivered the
treatment payload (it does not report the treatment token). What it does NOT
settle is an ambient memory read *in addition* to the scratch one — that is
prevented by the per-arm `HOME`/`CLAUDE_CONFIG_DIR` isolation, not by the
guard, for **two** reasons and not one. A probe asked for the magic words
with two in context may report either; and — the reason that covers the
commoner case — a contaminating source carrying no token of its own is
invisible to a token guard at all. The real `base.md` carries no token, and a
stale `~/.claude/CLAUDE.md` carries one no current run minted; both score
clean, measured. Only a real dispatch settles it. The decoy is what makes
that context carry two, so the guard prompt asks for **every** magic word
rather than "the magic word": a one-word answer from a contaminated control —
its decoy reported, the treatment token left unmentioned — is the case the
plural prompt exists for.

An arm that does not report the token IT was delivered, an arm that reports a
token it was *not* delivered (a control arm reporting the treatment token, or
a treatment arm reporting the control's decoy — the same isolation failure
seen from the other side), or a probe that could not run at all, is
**INCONCLUSIVE**: the summary carries
`guard: {expected, observed, contaminated}`, no score is written for that arm,
and the run exits `2`. Never PASS, never FAIL. Two cheap calls per pair.
The harness also refuses outright to point a delivery at the real `~/.claude`,
and the hermetic suite asserts a whole run leaves the real file
byte-identical.

Guidance content is **executed** by the arm — that is what the subject
measures, and `eval.yml`'s header states it as the trust boundary a guidance
dispatch accepts — but the harness **reads** that content only from inside the
`_agent-guidance` checkout it was pointed at: every manifest `file:` is
resolved with its symlinks followed and refused if it lands outside the
checkout root. The two are different boundaries and the second is not implied
by the first: a manifest row naming `../OUTSIDE_SECRET.md` was read,
delivered, and written verbatim into
`results/guidance/<key>/<ts>/<arm>/transcripts/raw.json`, which `main` pushes
to the public `eval-results` branch — so a row could publish any file the
runner can read.

## Out of scope

- `GHA-bench` as the harness (#18 caveat) — this is a dedicated harness.
