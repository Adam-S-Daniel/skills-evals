# Evals programme: handoff and current state

**Read this first.** This is the one place that describes the whole
systematic-evals effort (skills and fleet guidance, six epics across five
repositories), where it stands, what is parked and why, and how to pick it up.
It was written by the orchestrator session when Adam paused the programme on
2026-09-08 (decision 9 below). Everything here was read from GitHub or from a
child session at the stated time; nothing is reconstructed from memory.

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
| [skills-evals#60](https://github.com/Adam-S-Daniel/skills-evals/issues/60) | Coverage: harness resolves any registry, census, gate, scaffold | #63 (closed), #64, agentskills#153, #65 |
| [skills-evals#61](https://github.com/Adam-S-Daniel/skills-evals/issues/61) | Systematic runs: multi-fixture N trials, model roster, matrix, regression, gates, improvement loop, explorer, docs | #66, #67, #68, #69, #70, #71, #72, adamdaniel.ai#3536, #73 |
| [skills-evals#62](https://github.com/Adam-S-Daniel/skills-evals/issues/62) | One fixture per skill (21) plus cms-platform#408 | #74 to #94, cms-platform#408 — **STOPPED by decision 8** |
| [_agent-guidance#118](https://github.com/Adam-S-Daniel/_agent-guidance/issues/118) | Guidance subject: manifest, harness, touch gate, scaffold, InstructionsLoaded receipts | _agent-guidance#119 (closed), #97, _agent-guidance#120 (closed), #98, _agent-guidance#123, #139 |
| [skills-evals#95](https://github.com/Adam-S-Daniel/skills-evals/issues/95) | Guidance systematic runs: matrix, regression, improvement loop, explorer view, gates, site page, docs | #99, #121, #122, #123, #124, adamdaniel.ai#3538, #125 |
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
- **Gates**: _agent-guidance#119 → #120 (both merged); agentskills#153 after #64.
- **Explorer and site**: #72 → adamdaniel.ai#3536 → #123 → adamdaniel.ai#3538;
  the site PRs park on Adam's approval of the regression-review environment gate.
- **Docs last**: #73, #125.

## 2. Where it stands (2026-09-08, the pause)

### Merged and verified (nine PRs)

Each was merged with a merge commit after the check-run conclusions and the
combined status on its head were read, its verifier re-run in a fresh worktree
with the count matching the PR body, and its review class clean. Details and
run links are on the board and in each PR body.

| Issue | PR | Merge commit | Verified count | Note |
|---|---|---|---|---|
| _agent-guidance#119 section manifest + graduation gate (closed) | [_agent-guidance#121](https://github.com/Adam-S-Daniel/_agent-guidance/pull/121) | `5b371e3` | 1166 passed | post-merge `sync.yml` green |
| #63 harness resolves any registry layout (closed) | [#128](https://github.com/Adam-S-Daniel/skills-evals/pull/128) | `af06d0f` | 157 tests | |
| #82 rename-pdfs fixture | [#137](https://github.com/Adam-S-Daniel/skills-evals/pull/137) | `a6c882a` | 217 | real run stopped (decision 8) |
| #86 post-failure-comment fixture | [#134](https://github.com/Adam-S-Daniel/skills-evals/pull/134) | `8d131bd` | 305 | real run stopped |
| #85 github-actions-sha-pinning fixture + three scorer check types | [#133](https://github.com/Adam-S-Daniel/skills-evals/pull/133) | `c05d7de` | 379 | real run stopped |
| _agent-guidance#120 touch gate (closed) | [_agent-guidance#122](https://github.com/Adam-S-Daniel/_agent-guidance/pull/122) | `3d972b4` | 1256 passed | |
| #77 disarm-inherited-reach fixture + `setup:` hook + six git-state checks | [#135](https://github.com/Adam-S-Daniel/skills-evals/pull/135) | `f82bd77` | 475 | real run stopped |
| #74 review-bash-ci-reliability fixture | [#132](https://github.com/Adam-S-Daniel/skills-evals/pull/132) | `d5e06ee` | 588 | real run stopped |
| #80 writing-adrs, two fixtures | [#136](https://github.com/Adam-S-Daniel/skills-evals/pull/136) | `7c966ba` | 673 | real run stopped |

`main` of skills-evals is `7c966ba`; `main` of _agent-guidance is `5f13def`.

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
The worker's own report (a PR comment) is the last thing it posts; read it before round 4. **Next step**: round 4,
both halves (the `sync.yml` door read against the security header), prompts at
`.orchestration/2026-09-07/prompts/` for #124 round 3. CLEAN → fresh CI read →
merge → read the `sync.yml` run it triggers by conclusion → close #123. NOT
CLEAN → fix round 4, the last of three.

### Parked on Adam (exact action on the board's "Blocked on Adam" section)

| PR | Issue | State | Adam's action |
|---|---|---|---|
| [#129](https://github.com/Adam-S-Daniel/skills-evals/pull/129) | #67 model roster (harness lane) | 12 rounds, all NOT CLEAN; two-strikes fired seven times; fix rounds 9 to 11 were the renewed budget; round 12 NOT CLEAN on both halves (adversarial: two blockers needing only `previous.json`; code half: recommends merge, the prose is the defect) | reply 1, 2 or 3 on [the park comment](https://github.com/Adam-S-Daniel/skills-evals/pull/129#issuecomment-5576912058): one more scoped fix round (recommended), merge as is plus a follow-up issue, or something else |
| [#130](https://github.com/Adam-S-Daniel/skills-evals/pull/130) | #84 cms-stuck-pr-triage + the shared fake `gh` | round 5 code CLEAN, adversarial one documentation should-fix; budget spent; STOPPED by decision 8 | close, or reopen the lane ([the park comment](https://github.com/Adam-S-Daniel/skills-evals/pull/130#issuecomment-5555337295)) |
| [#131](https://github.com/Adam-S-Daniel/skills-evals/pull/131) | #81 adam-writing-style, the Class C pilot | round 6 NOT CLEAN on both halves (the provenance rule is defeated at cost 1/R; composition belongs to the pairwise judge #97 wires in); budget spent; STOPPED by decision 8 | close, or reopen the lane ([the park comment](https://github.com/Adam-S-Daniel/skills-evals/pull/131#issuecomment-5555421442)) |

Both parked fixture branches conflict with `main` (#130 in `run_eval.py`, #131 in
one import line); rule 22 gives each a merge-main step by a worker before any
further review.

### Stopped by decision 8 (2026-09-08 01:20 UTC): "Stop adding and completing evals for specific skills"

Epic #62 in full: no dispatch on #75, #76, #78, #79, #83, #87 to #94 or
cms-platform#408; #130 and #131 stay parked as stopped; the real N=3 runs and
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
- Gates: agentskills#153 (after #64).
- Explorer and site: #72, adamdaniel.ai#3536, #123, adamdaniel.ai#3538.
- Docs: #73, #125.

### Adam's decisions in force

1. "1" on PR #132 (03:21 09-05): one more fix round (done).
2. ~04:10 09-05, chat: "I authorize 3 additional rounds for PR 132 and
   pre-emptively for any (each) additional PR that needs them." Read as a
   budget of three fix rounds per PR beyond the two-strikes park. Budgets at the
   pause: #132 3/3 merged; #131 3/3 parked; #134 2/3 merged; #130 3/3 parked;
   _agent-guidance#122 1/3 merged; #136 3/3 merged; #138 3/3 (the third running
   at the pause); _agent-guidance#124 2/3 (the second running at the pause).
3. 15:49 09-05: "1. Continue as before 2. Merge with the commits": the
   empty-wave hold lifted; no history rewrite of real-address commits.
4. "1" on PR #129 (17:07 09-05): a fresh budget of three for #129 (spent).
5. 20:03 to 21:04 09-05: identify InstructionsLoaded-hook uses and implement via
   agents → skills-evals#139 and _agent-guidance#123 opened as sub-issues of #118.
6. 00:50 09-06: a 1.5-day pause (resumed 17:10 09-07).
7. "What percentage of the way done?" → answered 15 to 20%.
8. 01:20 09-08: stop adding and completing evals for specific skills (above);
   at 02:10 Adam confirmed the guidance fixtures (#100 to #120) count too.
9. 01:40 09-08: bring everything to the best stopping place within 10% more of
   the weekly allowance; one place to get up to speed (this file).

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

- Spend at the pause: orchestrator about $2,000 (127 review subagents inside
  it), workers about $1,180 across 88 child sessions (55 Sonnet 5, 33 Opus 5)
  plus the two Opus sessions running at the pause. Total about $3,200 over
  roughly 38 running hours on 09-04 to 09-08 (a 5.5-hour rate-limit outage and
  a 40-hour pause excluded).
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
findings.

## 7. Resume checklist

1. Read the board's latest body ([#126](https://github.com/Adam-S-Daniel/skills-evals/issues/126))
   and the last entries of `state-log.md` on `claude/orchestration-state`.
2. Confirm reach: skills-evals, _agent-guidance, agentskills, cms-platform and
   adamdaniel.ai attached; the session-provisioned GitHub connector present.
3. Read Adam's answers: the three park comments (#129, #130, #131) and the
   board's comments.
4. For #138 and _agent-guidance#124: re-verify the head in a fresh worktree
   (section 3), read CI, then launch the next review round from the prompts on
   the snapshot branch with the head's md5s filled in.
5. Re-set `/goal` with the condition at the bottom of the board if it was
   cleared; schedule the hourly wake; rewrite the board with a dated state.
6. Keep one message to Adam per wave: merged, running, blocked on him, spend,
   next wave. Anything named gets its link.
