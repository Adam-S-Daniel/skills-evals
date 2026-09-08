# Evals programme: handoff and current state

**Read this first.** This is the one place that describes the whole
systematic-evals effort (skills and fleet guidance, six epics across five
repositories), where it stands, what is parked and why, and how to pick it up.
It was written by the orchestrator session when Adam paused the programme on
2026-09-08 (decision 9 below) and **last updated on 2026-09-08 after the
parked-PR wave** (decision 10): Adam answered all three park comments with "1",
#131 and #130 merged, and #129 is in flight. Everything here was read from
GitHub or measured directly at the stated time; nothing is reconstructed from
memory.

- **Live operational state** (rewritten hourly while the programme ran, final
  at the pause): the status board,
  [skills-evals#126](https://github.com/Adam-S-Daniel/skills-evals/issues/126),
  marker `<!-- skills-evals:orchestration -->`. Its last body is the
  authoritative state; this file is the map to it.
- **Every review report, worker brief, review prompt and verification log**:
  the branch
  [`claude/orchestration-state`](https://github.com/Adam-S-Daniel/skills-evals/tree/claude/orchestration-state/.orchestration)
  (reference only, never merged), laid out as
  `.orchestration/<YYYY-MM-DD>/{briefs,prompts,reviews,verify,ctx}/` plus
  `state-log.md`, the orchestrator's append-only chronological log.
- **Per-PR history**: every PR the programme opened carries an orchestrator
  status blockquote at the top of its body and a "Review rounds" record with
  each round's findings, fix-round session links and verified counts.

## 1. What the programme is

Two subjects share one harness in
[skills-evals](https://github.com/Adam-S-Daniel/skills-evals):

- **Skills**: fixtures that measure whether a skill from the fleet's registries
  ([agentskills](https://github.com/Adam-S-Daniel/agentskills), cms-platform,
  adamdaniel.ai, agentskills-private) changes an agent's behaviour, scored by
  objective checks (`harness/objective.py`) and, for judgment classes, a blind
  pairwise judge (`harness/judge.py`). Classes: A = objective checks on a
  workspace, B = a faked delivery surface (the shared fake `gh`), C = judge-carried.
- **Guidance**: the same harness with `subject: guidance`, delivering a section
  of `_agent-guidance`'s `agents-md/base.md` through the real `fleet-memory.sh`
  hook in one of five modes (`none`, `stub`, `section`, `full`,
  `full-minus-section`) and measuring the section's effect on behaviour, with a
  per-arm delivery guard.

Real runs happen only through `eval.yml` on `main` (a WIF-federated Anthropic
key; the schedule and a `workflow_dispatch` input `fixture`, the latter added by
#97, not yet merged). Results publish to the unprotected `eval-results` branch.
Worker containers run as root and cannot run the real CLI, so every PR merges
hermetic and its issue stays open until a real run exists.

### The six epics and their sub-issues (69 in total)

| Epic | Scope | Sub-issues |
|---|---|---|
| [skills-evals#60](https://github.com/Adam-S-Daniel/skills-evals/issues/60) | Coverage: harness resolves any registry, census, gate, scaffold | #63 (closed), #64, [agentskills#153](https://github.com/Adam-S-Daniel/agentskills/issues/153), #65 |
| [skills-evals#61](https://github.com/Adam-S-Daniel/skills-evals/issues/61) | Systematic runs: multi-fixture N trials, model roster, matrix, regression, gates, improvement loop, explorer, docs | #66, #67, #68, #69, #70, #71, #72, [adamdaniel.ai#3536](https://github.com/Adam-S-Daniel/adamdaniel.ai/issues/3536), #73 |
| [skills-evals#62](https://github.com/Adam-S-Daniel/skills-evals/issues/62) | One fixture per skill (21) plus [cms-platform#408](https://github.com/Adam-S-Daniel/cms-platform/issues/408) | #74 to #94, [cms-platform#408](https://github.com/Adam-S-Daniel/cms-platform/issues/408) — **STOPPED by decision 8** |
| [_agent-guidance#118](https://github.com/Adam-S-Daniel/_agent-guidance/issues/118) | Guidance subject: manifest, harness, touch gate, scaffold, InstructionsLoaded receipts | _agent-guidance#119 (closed), #97, _agent-guidance#120 (closed), #98, _agent-guidance#123, #139 |
| [skills-evals#95](https://github.com/Adam-S-Daniel/skills-evals/issues/95) | Guidance systematic runs: matrix, regression, improvement loop, explorer view, gates, site page, docs | #99, #121, #122, #123, #124, [adamdaniel.ai#3538](https://github.com/Adam-S-Daniel/adamdaniel.ai/issues/3538), #125 |
| [skills-evals#96](https://github.com/Adam-S-Daniel/skills-evals/issues/96) | One fixture per guidance section (21) | #100 to #120 — **STOPPED by decision 8** (Adam ruled them evals for specific skills, 02:10 09-08) |

Every sub-issue's first line names its model (`claude-sonnet-5` or
`claude-opus-5`) and effort; its body carries a definition of done with a named
verifier and its dependencies. Unqualified `#n` above means skills-evals.

### Lanes and ordering (from the operating brief)

- **Harness lane, strictly one at a time** (they all edit `run_eval.py`,
  `eval.yml`, `propagation.yml`, `test/run_tests.py`):
  #63 → #97 → #66 → #67 → #64 → #68 → #99 → #69 → #121 → #70 → #124 → #71 →
  #122 → #65 → #98. #139 was inserted after #97 (decision 5).
- **Fixture lane, up to three in parallel, additive files only**: skills
  #74 to #94 in the order #62 gives (#84 first, it builds the shared fake `gh`);
  guidance #100 to #120 in the order #96 gives (#112 first). A guidance
  fixture's real N=3 run waits for #97.
- **Gates**: _agent-guidance#119 → #120 (both merged); [agentskills#153](https://github.com/Adam-S-Daniel/agentskills/issues/153) after #64.
- **Explorer and site**: #72 → [adamdaniel.ai#3536](https://github.com/Adam-S-Daniel/adamdaniel.ai/issues/3536) → #123 → [adamdaniel.ai#3538](https://github.com/Adam-S-Daniel/adamdaniel.ai/issues/3538);
  the site PRs park on Adam's approval of the regression-review environment gate.
- **Docs last**: #73, #125.

## 2. Where it stands (2026-09-08, after the parked-PR wave)

### Merged and verified (eleven PRs)

Each was merged with a merge commit after the check-run conclusions and the
combined status on its head were read, its verifier re-run in a fresh worktree
with the count matching the PR body, and its review class clean. Details and
run links are on the board and in each PR body.

| Issue | PR | Merge commit | Verified count | Note |
|---|---|---|---|---|
| _agent-guidance#119 section manifest + graduation gate (closed) | [_agent-guidance#121](https://github.com/Adam-S-Daniel/_agent-guidance/pull/121) | `5b371e3` | 1166 passed | the post-merge `sync.yml` run ([33921229215](https://github.com/Adam-S-Daniel/_agent-guidance/actions/runs/33921229215)) read as success by the orchestrator on 09-04 |
| #63 harness resolves any registry layout (closed) | [#128](https://github.com/Adam-S-Daniel/skills-evals/pull/128) | `af06d0f` | 157 tests | |
| #82 rename-pdfs fixture | [#137](https://github.com/Adam-S-Daniel/skills-evals/pull/137) | `a6c882a` | 217 | real run stopped (decision 8) |
| #86 post-failure-comment fixture | [#134](https://github.com/Adam-S-Daniel/skills-evals/pull/134) | `8d131bd` | 305 | real run stopped |
| #85 github-actions-sha-pinning fixture + three scorer check types | [#133](https://github.com/Adam-S-Daniel/skills-evals/pull/133) | `c05d7de` | 379 | real run stopped |
| _agent-guidance#120 touch gate (closed) | [_agent-guidance#122](https://github.com/Adam-S-Daniel/_agent-guidance/pull/122) | `3d972b4` | 1256 passed | |
| #77 disarm-inherited-reach fixture + `setup:` hook + six git-state checks | [#135](https://github.com/Adam-S-Daniel/skills-evals/pull/135) | `f82bd77` | 475 | real run stopped |
| #74 review-bash-ci-reliability fixture | [#132](https://github.com/Adam-S-Daniel/skills-evals/pull/132) | `d5e06ee` | 588 | real run stopped |
| #80 writing-adrs, two fixtures | [#136](https://github.com/Adam-S-Daniel/skills-evals/pull/136) | `7c966ba` | 673 | real run stopped |

| #81 adam-writing-style, three Class C fixtures + the judge mode | [#131](https://github.com/Adam-S-Daniel/skills-evals/pull/131) | `d13166d` | 863 | round 8 code review; real run stopped |
| #84 cms-stuck-pr-triage + the shared fake `gh` | [#130](https://github.com/Adam-S-Daniel/skills-evals/pull/130) | `700f48a` | 836 | round 6 code review; real run stopped |

`main` of skills-evals is `700f48a`; `main` of _agent-guidance is `5f13def`.

### In flight at the pause (two PRs, neither merged)

Both touch a key-bearing workflow, so each needs a clean one-way-door review
(an opus code review at high plus a separately prompted adversarial opus round,
plus the orchestrator's line-by-line read against the workflow security header)
before it can merge. The pause budget did not cover another review round.

**[PR #138](https://github.com/Adam-S-Daniel/skills-evals/pull/138) — issue #97,
the guidance subject and the `fixture` dispatch input.** Branch
`claude/skills-evals-97`. Four review rounds, every one NOT CLEAN (rounds 2 to 4
with no blocker; the recurring shape was a fix landing where the brief pointed
while the defect walked in beside it). Fix round 4, the last of Adam's three
authorized rounds, ran under the rule "every remedy checks the SINK, not an
enumeration of sources": `check_timeout` on entry to every subprocess-timeout
function, `_run_suite` standing down itself as the one runner spawner pinned by
an `rglob` AST walk over `test/` and `harness/`, every guidance path through
`inside_checkout`, typed fixture root and `env:`, arm-name cap, the fit test's
judge key by AST. Fix 4 LANDED on `b583341` (seven commits, one per item, worker report on the PR) and was VERIFIED by the orchestrator at 02:33 on 09-08 in a fresh worktree: 825 tests (2 skipped) exit 0, propagation 164, all eleven skill fixtures identical per check to `main`, `.github/` and `evals/` unchanged since `f9115ce`, merge-tree clean; CI green on the head with the same 825.
**Next step for whoever resumes**: round 5, both halves, hollowness against
`f9115ce`, using the round-4 prompts on the snapshot branch
(`.orchestration/2026-09-07/prompts/97-13-*.md`, `97-14-*.md`) with the new
head's md5s. CLEAN on both halves → fresh CI read → merge with a merge commit
(`expectedHeadSha` = the head) → the first real `eval.yml` dispatch on `main`
(`workflow-path-audit` on the schedule's default, then any fixture through the
`fixture` input) → #139. NOT CLEAN → the PR parks on Adam (budget spent). What
this PR carries is described in its body's "What" section.

**[_agent-guidance PR #124](https://github.com/Adam-S-Daniel/_agent-guidance/pull/124)
— _agent-guidance#123, the InstructionsLoaded load-time receipt.** Branch
`claude/agent-guidance-123` (no leading underscore). Three review rounds, none
clean (round 3: a regression through the brief's own remedy, a symlinked
`settings.json` classified unparseable flipping delivery off). Fix round 3 (the
second of three) at the pause: thirteen commits `df01967..8ec4cb3` landed (the symlinked
`settings.json` regression, the receipt claim, the two fleet-run abort shapes, the
regression floor under the basename gate, the octal `TIMEOUT`, the state-file and
payload guards, two docs commits; all noreply); the orchestrator VERIFIED `8ec4cb3` at
03:12 on 09-08 in a fresh worktree with the pinned yq: `./test/run-tests.sh` 1716
passed, 0 failed (1584 on `0d73ac4`), the three gates exit 0 (28 gap, 1 skipped, 0
covered), `.github/` unchanged since `0d73ac4`, `main` an ancestor, merge-tree clean.
The worker was interrupted at 03:27 on 09-08, inside its mutation battery, under decision 9's budget line (cost $32.99), so it posted no report of its own; the thirteen commits, their messages and the orchestrator's verification are the record. Its dispatch brief (`.orchestration/2026-09-07/briefs/123-fix3.md` on the snapshot branch) lists what each item had to prove. **Next step**: round 4,
both halves (the `sync.yml` door read against the security header), prompts at
`.orchestration/2026-09-07/prompts/` for #124 round 3. CLEAN → fresh CI read →
merge → read the `sync.yml` run it triggers by conclusion → close #123. NOT
CLEAN → fix round 4, the last of three.

### The parked-PR wave (2026-09-08, decision 10) — RESOLVED for two of three

Adam's reply to all three park comments was **1**. What "1" meant differed per
PR, because each park comment offered its own numbered options:

| PR | Option 1 was | Outcome |
|---|---|---|
| [#131](https://github.com/Adam-S-Daniel/skills-evals/pull/131) (#81) | make the objective check honest and merge; let the judge carry the defence | **MERGED** `d13166d`. Fix round 7 + round 8 code review (0 blocker, 1 should-fix, 4 nits) + a prose-only correction round. |
| [#130](https://github.com/Adam-S-Daniel/skills-evals/pull/130) (#84) | one fix round, documentation and nits only | **MERGED** `700f48a`. Fix round 6 + round 6 code review (0 blocker, 2 should-fix, 3 nits) + a correction round adding one test. |
| [#129](https://github.com/Adam-S-Daniel/skills-evals/pull/129) (#67) | one more fix round scoped to the adversarial fix list; round 13 decides | **IN FLIGHT.** Fix round 12 landed `4790845` (954 tests). Merged onto the new `main` twice as `22830cb`. Round 13 not yet run. |

**Answering a park comment with option 1 carried that PR to a merge; it did not
reopen epic #62 or #96.** Nothing else in either lane was dispatched, and the
real N=3 runs owed for the now-eight merged skill fixtures are still not
pursued. #81 and #84 stay OPEN as "merged hermetic; real run stopped".

#### #129's state, precisely (this is where a resuming session starts)

Branch `claude/skills-evals-67` at `22830cb`, pushed. Fix round 12 closed both
round-12 blockers, the three should-fixes and the four nits, and added the
**class-floor table** the round was gated on: inputs enumerated *from the code*
(`_clean_previous_arms` reads `previous["arms"]` and `entry["id"]`;
`_clean_catalogue_seen` reads `previous["catalogue_seen"]`, `entry["id"]` and
`entry["last_seen"]`; nothing else in the file is read) — four inputs, ten rows,
both directions, each red-first with a red mutation.

Three things the fix worker reported against its own interest, all of which
round 13 must rule on:

1. **It departed from the reviewer's prescribed remedy.** A pure "denominators
   disagree by more than f" rule was measured wrong at both ends — at small f it
   refuses essentially every retirement (1,126 of 1,503 `compute_roster` calls in
   the suite sit above 0.5); at large f it permits a bounded false retirement.
   What shipped is **verdict disagreement AND the fraction**.
2. **It could not reproduce the round-12 adversarial half's should-fix-2
   falsifier** (a true 10.0% published as 100.0%). Its own falsifier is 10 points,
   not 90: 498 filler census keys hold a live arm at its true 6.7%, 499 publish
   16.7%. It asks that the 90-point figure be treated as unreproduced.
3. **One cell is open and pinned as open** by `test_the_one_cell_this_cannot_cover`:
   deleting a since-retired model from **both** lists drops its turns and publishes
   a true 5.0% as 100.0%. It is the *inflation* direction (seats a model,
   re-decided next run) where the blockers closed the *deflation* direction (which
   retires permanently). Closing it needs a trusted history the harness does not
   have.

**The merge onto the new `main` surfaced a real cross-branch defect, and it is
the most important open item on this PR.** `select_models()` is deliberately
FAIL CLOSED — its docstring: falling through to the CLI default *"publishes a
badge for a model nobody chose and makes every week-over-week comparison a
comparison against a different model."* Four tests that arrived from #130 and
#131 predate the roster and drive `run_eval.py` end to end with no `--model`,
no fixture pin and no roster present, so the merged suite went **RED (1307
tests, 4 failures)**. This is not a merge error: the first failure was already
present after the first merge, before `harness/run_eval.py` was touched.
**Ruling: `select_models()` does not change** — relaxing it undoes the point of
#67 — the four tests get a model pin instead, which the same docstring blesses.
A fix is in flight.

The open question handed to round 13 either way: **if a committed fixture pins
neither `model:` nor `judge.model:`, a real `eval.yml` dispatch fails closed
unless a roster is present.** A per-fixture pin table and a reading of what
`eval.yml` actually supplies were commissioned; that is what would bite on the
first real run after #97.

### Stopped by decision 8 (2026-09-08 01:20 UTC): "Stop adding and completing evals for specific skills"

Epic #62 in full: no dispatch on #75, #76, #78, #79, #83, #87 to #94 or
[cms-platform#408](https://github.com/Adam-S-Daniel/cms-platform/issues/408); #130 and #131 stay parked as stopped; the real N=3 runs and
`docs/skill-impact.md` entries owed for the six merged skill fixtures (#82,
#86, #85, #77, #74, #80) are not pursued. Those issues stay open as "merged
hermetic; real run stopped" until Adam closes them or reopens the lane. Epic
#96 in full (the guidance fixtures #100 to #120), by Adam's answer at 02:10 on
09-08 that they count as evals for specific skills: nothing dispatched. A
consequence for the remaining guidance systematic-runs work (#99, #121, #122,
#124, #98): until a fixture lane reopens, the only guidance fixture on `main`
after #97 merges is the `evals/guidance/_delivery` canary, so those issues can
be built and tested hermetically but have nothing real to run against.

### Not started

- Harness lane after #97: #139, #66, #64, #68, #99, #69, #121, #70, #124, #71,
  #122, #65, #98 (in that order; #67 parked).
- Gates: [agentskills#153](https://github.com/Adam-S-Daniel/agentskills/issues/153) (after #64).
- Explorer and site: #72, [adamdaniel.ai#3536](https://github.com/Adam-S-Daniel/adamdaniel.ai/issues/3536), #123, [adamdaniel.ai#3538](https://github.com/Adam-S-Daniel/adamdaniel.ai/issues/3538).
- Docs: #73, #125.

### Adam's decisions in force

1. "1" on PR #132 (03:21 09-05): one more fix round (done).
2. ~04:10 09-05, chat: "I authorize 3 additional rounds for PR 132 and
   pre-emptively for any (each) additional PR that needs them." Read as a
   budget of three fix rounds per PR beyond the two-strikes park. Budgets at the
   pause: #132 3/3 merged; #131 3/3 parked; #134 2/3 merged; #130 3/3 parked;
   _agent-guidance#122 1/3 merged; #136 3/3 merged; #138 3/3, all three landed (the third
   verified at 02:33 on 09-08); _agent-guidance#124 2/3, both landed (the second
   verified at 03:12 on 09-08). Neither PR has had its next review round.
3. 15:49 09-05: "1. Continue as before 2. Merge with the commits": the
   empty-wave hold lifted; no history rewrite of real-address commits.
4. "1" on PR #129 (17:07 09-05): a fresh budget of three for #129 (spent).
5. 20:03 to 21:04 09-05: identify InstructionsLoaded-hook uses and implement via
   agents → skills-evals#139 and _agent-guidance#123 opened as sub-issues of #118.
6. 00:50 09-06: a 40-hour pause (resumed 17:10 09-07).
7. "What percentage of the way done?" → answered 15 to 20%.
8. 01:20 09-08: stop adding and completing evals for specific skills (above);
   at 02:10 Adam confirmed the guidance fixtures (#100 to #120) count too.
9. 01:40 09-08: bring everything to the best stopping place within 10% more of
   the weekly allowance; one place to get up to speed (this file).
10. 2026-09-08, after the pause: process the three PRs parked on Adam, "in all 3
    cases, this is my reply to the park comment: 1", fetch and pull latest on all
    relevant repos first, and **cleanly pause within 8% of the weekly allowance**
    (about $205 on decision 9's calibration), updating this file, the board and
    every relevant issue and PR on the way out. Two merged, #129 in flight.

## 3. How the programme is run (the rules that emerged, condensed)

The operating brief lives in the orchestrator session's system prompt, not in
any repo; its load-bearing content is restated here. The full standing rules
(9 to 30) and amendments (1 to 8) are on the board under "Amendments".

**Roles.** One orchestrator session plans, dispatches, reviews, merges and
verifies. It never writes implementation code, never commits into a branch a
worker holds, never force-pushes, never merges on a watch's exit code, never
adds `pull_request` to a key-bearing workflow, never creates or copies a
credential, never widens adamdaniel.ai's visual-regression skip lists, never
reports a repo, PR or branch as gone on a 404.

**Dispatching.** One child remote session per sub-issue (`create_session`,
model from the issue's first line, never `environment_id`; tag
`evals-orchestration`, title `<repo>#<issue>`), at most four at once. Every
brief: the issue URL; branch `claude/<repo>-<issue>`; `add_repo` any second repo
the issue names; read the repo's AGENTS.md first; commit and push as you go;
run the named verifier and put its exit code and count in the PR body; merge
`origin/main` into the branch before opening the PR; PR ready for review with
What / Verifier output / What I could not do; do NOT merge; tests in a class
named after the issue; `example.com`/`example.net` only in fixtures; no
credential copied anywhere; report BLOCKED rather than partial work; print
`CLAUDE_CODE_EFFORT_LEVEL` in the first report; the noreply commit identity
`4205216+Adam-S-Daniel@users.noreply.github.com`; no amend, rebase or
force-push. Fix rounds are new sessions with a "Branch state" paragraph and
every item stated as an invariant over its whole surface (since #138 round 4:
the check sits at the SINK, and the report shows a source of the worker's own
invention being refused). Findings reach a worker only through a fresh
session's brief. Briefs are kept under `.orchestration/<date>/briefs/`.

**Reviewing.** Fixtures and docs: a sonnet `/code-review` subagent at medium
(escalated to opus at high under amendment 5, effort compensation) plus the
orchestrator's read that the fixture prompt names no rule and no objective
check asks a regex to decide code shape. Harness, scorer, script and CI: an
opus `/code-review` at high plus the orchestrator's read of every shared file.
One-way doors (`eval.yml`, `sync.yml`, anything with OIDC, anything writing to
another repo, the agentskills renames map, manifest ids): an adversarial opus
round in addition, and a line-by-line read against the security header: every
`uses:` a bare 40-hex SHA, no `${{ }}` in a `run:` block, no `pull_request` on
a key-bearing workflow, minimal permissions, step-local push auth, no
concurrency group on a required context. Reviewers work read-only in a
`git archive` export md5-checked before launch, under a throwaway `HOME`
(`SKILLS_EVALS_USER_MEMORY` at a throwaway file; `CLAUDE_CONFIG_DIR` under it
for _agent-guidance), record `md5sum /root/.claude/CLAUDE.md` before and after,
never run a real `claude` or `gh`, never `scripts/sync.sh` against a real repo
(fixture bare repos only, `GH_TOKEN`/`GITHUB_TOKEN` unset), kill their
background processes, post nothing to GitHub. A should-fix is NOT CLEAN; a
nit-only report is CLEAN. Prompts are kept under `.orchestration/<date>/prompts/`.

**Two strikes and budgets.** A round-N finding that returns in round N+1 as the
same defect at the same severity with the same fix parks the PR; a defect that
returns through the brief's own prescribed remedy counts as a repeat. Adam's
decision 2 converts a park into three further fix rounds per PR, after which the
PR parks for real. Fired 28 times so far. Every merge needs the review clean;
a PR that fails review twice for the same reason, an eval run failing on the
spend cap, or two consecutive waves merging nothing stops the programme and is
reported to Adam at once (recurrences from a cause he has judged are reported,
not re-held).

**Verifying a head (the pre-merge procedure).** Fetch with an explicit refspec,
`git worktree add --detach`, assert the worktree sha equals the PR head,
fingerprint the files under test before and after
(`find … -print0 | sort -z | xargs -0 md5sum | md5sum`), run the verifier the
issue names, compare the count with the PR body (a mismatch is a stop), then
`git merge-tree --write-tree origin/main <sha>` and
`git merge-base --is-ancestor`. Read BOTH `pull_request_read get_check_runs`
and `get_status` on the current head (the combined status is always "pending
over zero statuses" here; the check runs carry the conclusions). Merge with
`merge_method: merge` and `expectedHeadSha`; confirm the commit is an ancestor
of `main`.

- skills-evals: `python3 -m pip install --user markdown-it-py==4.2.0`; siblings
  `../_agent-guidance` and `../agentskills` checked out (without the second one
  test skips); `python3 test/run_tests.py` (serial per checkout: the suite
  plants probe modules in `test/issues/`), `python3 test/test_propagation.py`
  (164, 1 skipped); every skill fixture under `evals/` compared per check
  against `main` under `--arm objective-only` (rule 19).
- _agent-guidance: mikefarah `yq` v4.53.3 first on `PATH` (the container's
  default `yq` is the wrong implementation), `npm ci --ignore-scripts`,
  `./test/run-tests.sh`; gates `bash scripts/check-agents-md.sh`,
  `node scripts/check-guidance-coverage.js --check-bytes`,
  `node scripts/check-registry.js`. A red verifier is re-run on the reviewed
  base head under the same environment before the branch is blamed (rule 28).

**Wake mechanics.** Hourly `send_later` wakes into the orchestrator session
(exactly one pending; `list_triggers` first); each wake reads every child with
`get_session`, PR state, check runs and combined status, acts, rewrites the
board (65,536-character limit; the board is trimmed rather than split), then
schedules the next wake. The `/goal` condition is copied verbatim at the bottom
of the board so it can be re-set with `/goal` if the harness clears it. A rate
limit reading other than `allowed` records `resetsAt` and does not count as a
wave (amendment 3).

## 4. Costs and the allowance

- Spend at the pause: orchestrator about $2,020 (128 review subagents inside
  it), workers $1,262 across 88 child sessions (55 Sonnet 5, 33 Opus 5), the
  last two being the fix rounds that landed at the pause ($54.75 and $32.99).
  Total about $3,280 over roughly 40 running hours on 09-04 to 09-08 (a
  5.5-hour rate-limit outage and a 40-hour pause excluded).
- Calibration to the weekly allowance: $2,378 of programme spend read 93% of
  the seven-day window at the 09-06 pause, so one allowance is about $2,560 of
  this usage if the programme is the account's whole use.
- Measured unit costs: about $27 per review round (subagents plus the
  orchestrator's own turns, 74 rounds), $30 to $50 per Opus fix round, $3 to
  $15 per Sonnet fix round; fixture PRs averaged 5.4 rounds and $67 of worker
  cost; harness PRs 4 to 12 rounds and $25 to $300 of worker cost.
- Estimate for everything not stopped (the harness lane $5,500 to $9,400; the
  guidance subject, gates, explorer, site and docs $1,700 to $2,900): $7,200 to
  $12,300, about 3 to 5 weekly allowances at the measured rates. The stopped
  guidance fixtures would have added $4,000 to $6,000. Two levers cut it: drop
  the second review half on non-security harness PRs (about a third of review
  spend), and cap fix rounds at two per PR before parking.
- Real `eval.yml` runs draw on the workspace API key through WIF, not on the
  weekly allowance; none has been dispatched by the programme yet (the first
  follows #97's merge). No spend-cap failure has been observed.

## 5. Facts learned that change the plan

The board's "Facts learned" section carries the full list; the ones a resumer
must know:

- Every fixture PR conflicts with every other at the same append points, and a
  merge can conflict semantically with no textual conflict: every review of a
  branch behind `main` drops `main`'s `objective.py` onto a copy of head.
- A heuristic that guesses identity fails review until it is removed; a denylist
  repeats the round it was written in; a cap ordered by anything the planter
  writes is re-ordered by the planter; a fixed-run provenance rule is defeated
  at cost 1/R. Each time the fix was a mechanical rule with a stated invariant.
- A fix that lands where the brief points can leave the door beside it open
  (#138 rounds 2 to 4). Briefs state invariants over whole surfaces and require
  the check at the sink.
- A test that builds a path beside its tempdir builds it at `/tmp`; every path a
  test creates lives under its own `mkdtemp` (rule 27).
- The account's five-hour rate limit, not the four-session cap, is the binding
  constraint; a session killed by it is archived and continued under the same
  round with an audit-then-finish brief (rule 30).
- The two GitHub connectors: `mcp__github__*` (session-provisioned, has Actions
  tools, `merge_pull_request`, review threads) is the one used; name the
  connector when reporting a check.

## 6. Owed follow-ups (not blocking, recorded)

`run_setup` through `expand()` (from the #130 merge-main step); the skill arm's
env allowlist as its own PR (#97 round 1 adversarial S6); #97 round 1's
record-only items; #136 round 7's nit (one clause in the N-b pin's comment,
`test/run_tests.py:4308-4309`); the record-only lists in each #138 and #124
round report; if Adam picks option 2 on #129, a follow-up issue for its
findings. Opened during the parked-PR wave and still open:
[#142](https://github.com/Adam-S-Daniel/skills-evals/issues/142) (a test asserts
an environment fact, so `main` fails locally where the fleet repos are cloned
side by side), [#143](https://github.com/Adam-S-Daniel/skills-evals/issues/143)
(`_read_matched` raises `PermissionError` on an unreadable file instead of
failing the check by name) and
[#144](https://github.com/Adam-S-Daniel/skills-evals/issues/144)
(`materialize_workspace` leaks its temp workspace on any exception that is not
`SetupFailedError`). Also owed: the round-8 review of #131 could not call a real
model, so **whether a judge actually ranks a spliced paste last — the premise
option 1 rests on — is unmeasured**; #97's first real dispatch is what validates
it.

## 7. Resume checklist

1. Read the board's latest body ([#126](https://github.com/Adam-S-Daniel/skills-evals/issues/126))
   and the last entries of `state-log.md` on `claude/orchestration-state`.
2. Confirm reach: skills-evals, _agent-guidance, agentskills, cms-platform and
   adamdaniel.ai attached; the session-provisioned GitHub connector present.
3. Read Adam's answers: the board's comments, and — for #129, the only park
   still live — the wave record in section 2 above.
4. For #129: the branch is `claude/skills-evals-67` at `22830cb`. Get the suite
   to exit 0 first (the four pre-roster tests above), then run round 13, both
   halves, on the merged head, ruling on the three self-reported items and the
   unpinned-fixture question. For #138 and _agent-guidance#124: re-verify the
   head in a fresh worktree (section 3), read CI, then launch the next review
   round from the prompts on the snapshot branch with the head's md5s filled in.
   **Run the suite from a git worktree under `.claude/worktrees/`, not from the
   repo root** — see [#142](https://github.com/Adam-S-Daniel/skills-evals/issues/142).
5. Re-set `/goal` with the condition at the bottom of the board if it was
   cleared; schedule the hourly wake; rewrite the board with a dated state.
6. Keep one message to Adam per wave: merged, running, blocked on him, spend,
   next wave. Anything named gets its link.
