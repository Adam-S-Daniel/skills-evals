# How the skills evals work, where to look, and what is left

A plain-English guide for someone who knows the fleet but has not worked in
this repository. The technical method is in [`DESIGN.md`](../DESIGN.md), the
operating record in [`HANDOFF.md`](../HANDOFF.md), and the live status board is
[issue #126](https://github.com/Adam-S-Daniel/skills-evals/issues/126).
Last revised 2026-09-22.

## 1. What the system does

Skills are reusable instruction files (recipe cards) that a coding agent
installs to do a class of task better. Fleet guidance is the same idea for
account-wide rules. This repository answers one question with numbers: **does
the agent do the job better with the card than without it?**

For each measured skill there is a **fixture**: a task prompt, a small
throwaway repository to work in, a list of objective checks, and a judge
rubric. A run takes the same model and has it do the task twice in two clean
copies of that repository, once with the skill installed and once without.
Then two scores are produced:

- **Objective checks** are scripted assertions on the finished workspace
  (files exist, YAML parses, a workflow would trigger on the right paths, a
  ruleset was not touched). They pass or fail and cannot be argued with.
- **The judge** is a second, stronger model that reads both transcripts and
  diffs and scores each arm on a few named dimensions (for example
  completeness, salience, restraint) from a rubric written into the fixture.
  It is the subjective half, kept honest by the objective half.

A badge summarises the last five runs: green if the with-skill arm beat the
without-skill arm, yellow for a tie or mixed signals, red if the skill hurt.

## 2. Which models run, and who decides

The models that compete (the **arms**), the **judge**, and the cheap
**preflight** model that proves the API token works are listed in
[`evals/roster.yml`](../evals/roster.yml) on `main`. That file is trusted
because `main` is pull-request only: nothing automated can change it.

Every run also *computes* what the roster should be, from two inputs: the
Models API (which models exist and how old they are) and a **usage census**
(which models this account actually runs, per week, published from a
workstation as `usage/latest.json` on the results branch). The computed
roster is only a **proposal**. When it differs from the committed file the run
pushes the proposed file to the bot-owned branch `roster/proposal` and keeps
one tracking issue open with every seat's reason and the numerator and
denominator behind it. A human opens a pull request from that branch and
merges it, or does not. See ADR
[0001](decisions/0001-roster-trusted-on-main.md) for why it is shaped this way.

## 3. When it runs, and what it costs to run

`.github/workflows/eval.yml` runs every Monday at 07:00 UTC and on manual
dispatch (`gh workflow run eval.yml --ref main`, optional input `fixture=`).
It bills the organisation's API workspace `skills-evals-ci` through workload
identity federation, not the Claude Code subscription. A measured run on
2026-09-22 (one fixture, one Sonnet 5 arm, Opus 4.8 judge) took 6 minutes 24
seconds wall clock and cost **$1.71**: Sonnet 5 arms $0.89, Opus 4.8 judge
$0.78, Haiku preflight $0.04. The judge is about 45% of a run.

## 4. Where to look for current results

Everything published lives on the unprotected
[`eval-results`](https://github.com/Adam-S-Daniel/skills-evals/tree/eval-results)
branch, which carries generated data only and is treated as untrusted input:

| Path on `eval-results` | What it is |
|---|---|
| `results/<fixture>/<timestamp>/report.md` | one page per run: prompt, per-arm objective score, judge score, cost, turns, duration |
| `results/<fixture>/<timestamp>/{with_skill,without_skill}/summary.json` | the raw numbers behind the report, including token usage and every check's detail |
| `badges/<fixture>.json` | the shields.io badge over the last five runs, rendered at the top of the README |
| `roster/latest.json` | the computed roster and proposal from the latest run (an exhibit, read by no decision) |
| `usage/latest.json` | the usage census |
| `propagation/` | the separate account-store audit |

The most recent real run at the time of writing is
[`results/workflow-path-audit/20260922T125552Z/report.md`](https://github.com/Adam-S-Daniel/skills-evals/blob/eval-results/results/workflow-path-audit/20260922T125552Z/report.md).
Raw transcripts are deliberately never published (public repository).

## 5. What is measured today

Every fixture below lives under `evals/` on `main`; each entry says what task the agent is given, what a good result looks like, how many scripted objective checks decide pass or fail and what they look at, which judge dimensions score the subjective half (with their weights), the pinned models, and whether a real run against the live CLI has happened yet (most have not: the scheduled run always targets `workflow-path-audit`, and decision 8 stopped the per-skill lanes). Inventory taken on 2026-09-22 at `main` `3515904`.

Two `evals/` directories aren't covered below because they aren't skill or guidance-subject fixtures: `evals/guidance-bridge-canary/`, a tool-free magic-word probe of the `CLAUDE.md -> @AGENTS.md` import, and `evals/propagation/`, a skill-delivery probe compared against `agentskills`' lockfile. Neither has a prompt, objective checks, or a judge rubric.

### adam-writing-style/proposal-bio

- `adam-writing-style` (registry: `agentskills`) — [evals/adam-writing-style/proposal-bio](https://github.com/Adam-S-Daniel/skills-evals/tree/main/evals/adam-writing-style/proposal-bio)
- Write a 60-word third-person proposal bio from background notes; good output is concrete (employer/dates, the named accessibility standard), third-person, and free of corporate filler.
- Objective (3): no avoid-list buzzwords survive; third-person with no first-person "I"; both the employment dates and the named standard (Section 508) are cited.
- Judge: pairwise rank (no weights) against references `in-voice`/`generic`; dimensions specificity, register match, absence of corporate filler.
- Model `claude-sonnet-5`; judge `claude-opus-4-8`. Class C. No real run yet.

### adam-writing-style/recruiter-reply

- `adam-writing-style` (registry: `agentskills`) — [evals/adam-writing-style/recruiter-reply](https://github.com/Adam-S-Daniel/skills-evals/tree/main/evals/adam-writing-style/recruiter-reply)
- Reply to a recruiter's cold email in the user's voice, declining but leaving the door open; good output greets by name, opens with a hedge rather than an assertion, and cites specifics from the material.
- Objective (4): no avoid-list buzzwords; greets the recruiter by name in the opening; opens with a hedge/apology, not an assertion; cites both the requisition number and the contract end date.
- Judge: pairwise rank (no weights) against `in-voice`/`generic`; dimensions specificity, register match, absence of corporate filler.
- Model `claude-sonnet-5`; judge `claude-opus-4-8`. Class C. No real run yet.

### adam-writing-style/self-appraisal-opening

- `adam-writing-style` (registry: `agentskills`) — [evals/adam-writing-style/self-appraisal-opening](https://github.com/Adam-S-Daniel/skills-evals/tree/main/evals/adam-writing-style/self-appraisal-opening)
- Draft the opening paragraph of a quarterly self-appraisal from notes; good output is first-person, narrative, generous toward collaborators, and specific about named systems and numbers.
- Objective (3): no avoid-list buzzwords; genuinely first-person (not narrated about the author); the named repository and pipeline-time figure from the notes are both cited.
- Judge: pairwise rank (no weights) against two references; dimensions specificity, register match, absence of corporate filler.
- Model `claude-sonnet-5`; judge `claude-opus-4-8`. Class C. No real run yet.

### cms-stuck-pr-triage

- `cms-stuck-pr-triage` (registry: `cms-platform`) — [evals/cms-stuck-pr-triage](https://github.com/Adam-S-Daniel/skills-evals/tree/main/evals/cms-stuck-pr-triage)
- Diagnose why a CMS publish loop "keeps failing" and say what to do about each open PR, using a fake replay-only `gh` CLI seeded with three PRs (one blocked by a missing required status check, one on a stale base, one that should be left alone). Good output names the right cause per PR and attempts no writes.
- Objective (7): #412's stale base/superseded commit named; #418's missing required status context named; no write aimed at #421; the fake `gh` was used with no write attempted overall; the failing run's log was actually read; the workflow files and the fake's own payloads stayed untouched.
- Judge: weighted — `root_cause` 0.4, `decisions` 0.4, `restraint` 0.2.
- Model `claude-sonnet-5`; judge `claude-opus-4-8`. Class B. No real run yet.

### disarm-inherited-reach

- `disarm-inherited-reach` (registry: `agentskills`) — [evals/disarm-inherited-reach](https://github.com/Adam-S-Daniel/skills-evals/tree/main/evals/disarm-inherited-reach)
- Set up a throwaway copy of a checkout so a destructive test script can't reach the real (prod) repo, then run it. Good output makes a genuine standalone copy (severing the inherited `origin`), runs the script only there, and reports the disarm plus an observed failed push.
- Objective (8): original checkout's remote/HEAD untouched; prod's history never moved; no leaked config anywhere still names prod; the script ran outside the armed locations, in a genuine standalone remote-free repo; the worktree list unchanged; the final reply names the severed remote and the failed push.
- Judge: weighted — `"procedure fidelity"` 0.5, `restraint` 0.2, `explanation` 0.3.
- Model `claude-sonnet-5`; judge `claude-opus-4-8`. Class A. No real run yet.

### github-actions-sha-pinning

- `github-actions-sha-pinning` (registry: `cms-platform`) — [evals/github-actions-sha-pinning](https://github.com/Adam-S-Daniel/skills-evals/tree/main/evals/github-actions-sha-pinning)
- Bring a repo's Actions pins into line with the fleet pinning policy. Good output pins every third-party action to the exact SHA `PINS.md` lists, strips trailing version comments, and leaves the repo's own `cms-platform` references on their release tag rather than converting them to a SHA.
- Objective (9): third-party `uses:` lines SHA-pinned and matching `PINS.md` exactly; no trailing comments; `cms-platform` refs stay on tag; local/docker refs and `PINS.md` byte-identical to seed; the three workflow/action files not deleted or gutted; everything parses as YAML.
- Judge: weighted — `carve_out` 0.4, `comment_removal` 0.3, `restraint` 0.3.
- Model `claude-sonnet-5`; judge `claude-opus-5`. Class A. No real run under this name; a predecessor fixture (`pin-actions-to-sha`, before its rewrite/reintroduction as this one under issue #85) has 6 real runs, latest 2026-08-17.

### guidance/_delivery

- Subject `guidance`, section `security` (`_agent-guidance` checkout) — [evals/guidance/_delivery](https://github.com/Adam-S-Daniel/skills-evals/tree/main/evals/guidance/_delivery)
- Not a behavioral A/B — a scheduled delivery canary asking a tool-free agent to report any "magic words" in its context, once per delivery mode (`none`, `stub`, `section`, `full`, `full-minus-section`). Good output reports exactly the token it was actually delivered, proving the fleet-memory hook really puts guidance into context the way it claims to.
- Objective (5, one per arm): the control shows its own decoy token and not the treatment token; each of the four treatment arms shows the treatment token for its mode.
- Judge: none — this fixture measures delivery, not quality.
- Model `claude-haiku-4-5` (cheapest model sufficient for a tool-free probe). No class label. 1 real run, latest 2026-09-13T22:16:38Z.

### post-failure-comment

- `post-failure-comment` (registry: `cms-platform`) — [evals/post-failure-comment](https://github.com/Adam-S-Daniel/skills-evals/tree/main/evals/post-failure-comment)
- Wire two Playwright CI workflows' failures into the platform's `post-failure-comment` composite action instead of an ad hoc inline `gh pr comment`, following its caller-side-gating convention (including a schedule-only workflow that shouldn't be touched). Good output uses correct `post`/`resolve` step pairs, matching markers, and correct `if:` gating per job shape.
- Objective (11): schedule-only workflow/vendored contract untouched; old inline comment block removed; single-job post/resolve steps wired correctly; multi-job report job wired on `needs:` not `job.status`; composite references resolve validly; markers don't collide; no raw event/input interpolation in `run:`; workflows parse as YAML.
- Judge: weighted — `convention_fidelity` 0.5, `gitleaks_explanation` 0.2, `restraint` 0.3.
- Model `claude-sonnet-5`; judge `claude-opus-4-8`. Class A. No real run yet.

### rename-pdfs

- `rename-pdfs` (registry: `agentskills`) — [evals/rename-pdfs](https://github.com/Adam-S-Daniel/skills-evals/tree/main/evals/rename-pdfs)
- Rename six seeded PDFs (a statement, an invoice with a decoy filename date, an already-conventional receipt, an image-only scan, a duplicate bill pair) to the user's `YYYYMMDD-Type-Issuer-Title.pdf` convention. Good output gets every date/type right, prefers the document body's date over a misleading filename date, disambiguates true duplicates, and leaves conventional or unreadable files alone.
- Objective (8): final `inbox/` listing matches exactly; every PDF's bytes survive by digest; five per-file digest checks confirm each file's bytes ended up under the right name (or stayed alone); nothing exists outside `inbox/`.
- Judge: weighted — `convention_fidelity` 0.5, `date_priority` 0.3, `restraint` 0.2.
- Model `claude-sonnet-5`; judge `claude-opus-4-8`. Class A. No real run yet.

### review-bash-ci-reliability

- `review-bash-ci-reliability` (registry: `agentskills`) — [evals/review-bash-ci-reliability](https://github.com/Adam-S-Daniel/skills-evals/tree/main/evals/review-bash-ci-reliability)
- Review a release pipeline's shell for reliability problems and fix them (seeded with an exit-status swallow via process substitution, a broken-pipe-prone `grep -q`, a swallowed `gh api` failure, missing git identity/signing setup, an unguarded `jq` dependency). Good output fixes the real bugs while leaving two decoys — an already-correct line and an optional cleanup line — untouched.
- Objective (10): workflow parses and exists; `gh run watch` status captured correctly; `grep -q` no longer pipe-fed; failed `gh api` call not silently read as "nothing found"; git identity configured; `jq` guaranteed or replaced; version-read logic survives; commit signing made CI-safe; both decoys untouched.
- Judge: weighted — `correctness` 0.5, `restraint` 0.2, `explanation` 0.3.
- Model `claude-sonnet-5`; judge `claude-opus-4-8`. Class A. No real run yet.

### windows-elevation-from-wsl

- `windows-elevation-from-wsl` (registry: `agentskills`) — [evals/windows-elevation-from-wsl](https://github.com/Adam-S-Daniel/skills-evals/tree/main/evals/windows-elevation-from-wsl)
- From inside WSL, move a scheduled Windows backup task's fire time and apply it to the live task, against a fake `powershell.exe`/`pwsh.exe` that simulates elevation prompts. Good output edits the script, never tries to dodge or force elevation from WSL, exports the live task before handoff, and tells the user the exact elevated command to run.
- Objective (7): script's default time moved (03:30, not 02:00); no elevation-dodge attempted; at most one denied write retried; task principal/run level not downgraded; live task exported before handoff; final reply names the need for elevation plus the exact command; fake binaries untouched.
- Judge: weighted — `diagnosis` 0.4, `handoff` 0.4, `restraint` 0.2.
- Model `claude-sonnet-5`; judge `claude-opus-4-8`. Class B. No real run yet.

### workflow-path-audit

- `workflow-path-audit` (registry: `agentskills`) — [evals/workflow-path-audit](https://github.com/Adam-S-Daniel/skills-evals/tree/main/evals/workflow-path-audit)
- Audit a repo's Actions workflows so each triggers only on files it depends on. Good output routes a docs-only change to just docs/tests, a source change to tests/deploy but not docs, a lockfile change to every installer, and a prose-only change to nothing but the required check — never filtering an event that ignores path filters, never touching the ruleset.
- Objective (8): four synthetic changesets checked against expected triggered/skipped workflows; the required-check workflow has no workflow-level filter and gates internally instead; all workflows parse as YAML; schedule/issue-only workflows gained no filter; the ruleset file untouched.
- Judge: weighted — `completeness` 0.5, `salience` 0.3, `restraint` 0.2.
- Model `claude-sonnet-5`; judge `claude-opus-4-8`. No class label (the repo's original pilot fixture, run weekly). 14 real runs, latest 2026-09-22T12:55:52Z.

### writing-adrs/bootstrap

- `writing-adrs` (registry: `agentskills`) — [evals/writing-adrs/bootstrap](https://github.com/Adam-S-Daniel/skills-evals/tree/main/evals/writing-adrs/bootstrap)
- Record a retry-policy decision as an ADR in a repo with no `docs/decisions/` yet. Good output bootstraps the folder with the skill's own template, writes ADR 0001, links it from the governed script and a new AGENTS.md pointer, and touches nothing else.
- Objective (9): bootstrapped README carries the skill's template headings; index gained a row for 0001; ADR sections in the skill's default order; governed script's header links the ADR and keeps its decision sentence; both links resolve; exactly one ADR file exists; nothing outside those paths changed; AGENTS.md gained the pointer.
- Judge: weighted — `decision-with-alternatives-and-consequences` 0.5, `title-is-a-decision-statement` 0.3, `restraint` 0.2.
- Model `claude-sonnet-5`; judge `claude-opus-4-8`. Class A (format half — no existing convention). No real run yet.

### writing-adrs/existing-convention

- `writing-adrs` (registry: `agentskills`) — [evals/writing-adrs/existing-convention](https://github.com/Adam-S-Daniel/skills-evals/tree/main/evals/writing-adrs/existing-convention)
- Same decision, but in a repo with three existing ADRs and its own house section order (Status/Context/Decision/Consequences), different from the skill's default. Good output follows the house convention, adds exactly one new ADR (0004), links it correctly, and leaves the rest untouched.
- Objective (7): new ADR follows house order, not the skill's default; index gained a row for 0004; governing script's header links it; both links resolve; exactly four ADR files exist in total; pre-existing ADRs, CHANGELOG.md, AGENTS.md, and root README.md all byte-identical to seed.
- Judge: weighted — `decision-with-alternatives-and-consequences` 0.5, `title-is-a-decision-statement` 0.3, `restraint` 0.2.
- Model `claude-sonnet-5`; judge `claude-opus-4-8`. Class A (format half — matches an existing convention). No real run yet.

## 6. What is finished

- The harness, scorers, roster, propagation audit and thirteen fixtures are
  merged on `main` with CI green.
- The roster redesign (PR #153) merged on 2026-09-21, the first real proposal
  run succeeded, and the census was published on 2026-09-22 so proposals are
  now usage-based.
- The test suite's guard against forking itself (issue #152, PR #163) merged
  after five review rounds; two clean-up follow-ups (PR #165) merged the same
  day.

## 7. What is left, what blocks it, and what it would cost

Costs are ranges. "Points" are percent of the weekly Claude Code allowance,
calibrated on 2026-09-21 when local sessions delivered the #152 merge (five
review rounds and three fix rounds) plus PR #165 for about six points;
earlier orchestrator-driven cloud sessions ran three to five times costlier
per round. Dollars are organisation API spend only, at today's one-arm roster
unless stated.

### Blocking decisions (Adam's)

1. **The roster proposal, [#162](https://github.com/Adam-S-Daniel/skills-evals/issues/162): decided.**
   Usage-based since 2026-09-22: Sonnet 5 (45.4% of rankable usage) and
   Opus 5 (45.2%) seated by share; Haiku 4.5 and Fable 5.1 seated by the
   newest-per-tier rule at 6.3% and 3.0%; judge Fable 5. **Adam approved
   it on 2026-09-22.** The remaining action is the human one ADR 0001
   reserves: open a pull request from `roster/proposal` (commit `c4a8bea`,
   changing only `evals/roster.yml`), let CI run, merge it. Not yet done at
   the time of writing. Once merged, a fixture run rises from about $1.7 to
   roughly $10–14 (four arms, a judge at twice Opus prices), and the Monday
   run stops re-proposing. No allowance cost.
2. **Whether to reopen the fixture lanes** ([#62](https://github.com/Adam-S-Daniel/skills-evals/issues/62),
   [#96](https://github.com/Adam-S-Daniel/skills-evals/issues/96)), stopped by
   decision 8 on 2026-09-08 ("stop adding and completing evals for specific
   skills"). Each new fixture was about 5 review rounds; at today's local
   rates 3–5 points each, 21 skills and 21 guidance sections outstanding.
3. **The guidance receipt, [_agent-guidance PR #124](https://github.com/Adam-S-Daniel/_agent-guidance/pull/124)**,
   parked with its fix budget spent and two reproduced defects. It holds
   [#139](https://github.com/Adam-S-Daniel/skills-evals/issues/139). Options:
   authorise one more fix round (2–3 points), redesign, or close.
4. **The Batch API step below**: go or no-go, given the reservations.

### Planned steps, in order

| # | Step | Allowance | Org API |
|---|---|---|---|
| 1 | **Move the judge calls to the Batch API from `eval.yml`.** Only the judge is batchable: each arm is an agentic loop where every turn depends on the previous tool result, and the Batch API takes independent single requests. The judge today is one `claude -p` call per arm; it would become one `messages.batches.create` with two requests, polled to completion inside the job. `eval.yml` is a one-way door, so it takes a worker, a code review and an adversarial review. | 3–6 points | about $5 of verification runs; then saves ~50% of judge spend, about $0.40 per run today and $1.50–2 per run on the proposed roster |
| 2 | Owed real runs (N=3) for the merged fixtures whose issues stay open for them: #82, #86, #85, #77, #74, #80, #84, #81. Dispatch and record only. **Held by decision 8 until Adam reopens.** | 1–2 points | about $40 at one arm, $250 on the proposed roster |
| 3 | [#166](https://github.com/Adam-S-Daniel/skills-evals/issues/166) suite-fork guard nits (test-only). | 1–2 points | none |
| 4 | [#139](https://github.com/Adam-S-Daniel/skills-evals/issues/139) receipts per arm. Blocked by decision 3 above. | 4–8 points | none |
| 5 | [#66](https://github.com/Adam-S-Daniel/skills-evals/issues/66) several fixtures per skill, N trials per arm, aggregated statistics. | 4–8 points | none to build; multiplies run cost by N |
| 6 | [#64](https://github.com/Adam-S-Daniel/skills-evals/issues/64) coverage census (covered / skipped / gap per registry). | 2–4 points | none |
| 7 | [#68](https://github.com/Adam-S-Daniel/skills-evals/issues/68) matrix runner: every covered skill × every roster model, budgeted, with an index; [#99](https://github.com/Adam-S-Daniel/skills-evals/issues/99) the guidance subject in it. | 8–16 points | weekly matrix about $25 at one arm and 13 skills; about $150 on the proposed roster; more with N trials |
| 8 | [#69](https://github.com/Adam-S-Daniel/skills-evals/issues/69), [#121](https://github.com/Adam-S-Daniel/skills-evals/issues/121) regression detection with one tracking issue per regression. | 6–12 points | none |
| 9 | [#70](https://github.com/Adam-S-Daniel/skills-evals/issues/70) gates that read the numbers; [agentskills#153](https://github.com/Adam-S-Daniel/agentskills/issues/153) the registry CI gate. | 4–7 points | none |
| 10 | [#71](https://github.com/Adam-S-Daniel/skills-evals/issues/71), [#122](https://github.com/Adam-S-Daniel/skills-evals/issues/122) improvement loop: propose an edit, measure on held-out fixtures, open the registry PR. | 12–24 points | $10–50 per proposal measured |
| 11 | [#65](https://github.com/Adam-S-Daniel/skills-evals/issues/65), [#98](https://github.com/Adam-S-Daniel/skills-evals/issues/98) auto-scaffold gaps into draft fixture PRs. Depends on decision 2. | 6–12 points | none |
| 12 | Explorer pages [#72](https://github.com/Adam-S-Daniel/skills-evals/issues/72), [#123](https://github.com/Adam-S-Daniel/skills-evals/issues/123), published via [adamdaniel.ai#3536](https://github.com/Adam-S-Daniel/adamdaniel.ai/issues/3536) and [#3538](https://github.com/Adam-S-Daniel/adamdaniel.ai/issues/3538). | 8–16 points | none |
| 13 | Docs and ADRs [#73](https://github.com/Adam-S-Daniel/skills-evals/issues/73), [#125](https://github.com/Adam-S-Daniel/skills-evals/issues/125). | 2–6 points | none |

Everything not held: roughly **60–120 points**, three to six weekly
allowances at today's local rates, spread over the order above. The
standing weekly run is about $1.70 on the current one-arm roster and
$10–14 once the approved #162 roster is merged, before any matrix or trials
multiplier; the dollar figures in the table assume the approved roster where
they say so.

### Standing holds

Decision 8 (no new skill-specific evals) and the guidance receipt park are in
force until Adam lifts them. Real runs bill the API workspace, never the
allowance; agent work bills the allowance, never the workspace.
