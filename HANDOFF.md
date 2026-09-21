# Evals programme: handoff and current state

**Read this first.** This is the one place that describes the whole
systematic-evals effort (skills and fleet guidance, six epics across five
repositories), where it stands, what is parked and why, and how to pick it up.
It was written by the orchestrator session when Adam paused the programme on
2026-09-08 (decision 9 below) and **last updated on 2026-09-15** (see § 0A; § 0 preserves the September 13 session, and the 2026-09-08 state after #129's
round 14, decision 11, follows it): #131 and #130 merged in the parked-PR wave, #129 ran a
fourteenth review round, was NOT CLEAN on both halves again, and is now answered
— revert round 14's ITEM 2, then redesign the roster's denominator around a
trusted history under
[#147](https://github.com/Adam-S-Daniel/skills-evals/issues/147). Everything here
was read from GitHub or measured directly at the stated time; nothing is
reconstructed from memory.

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

## 0B. Session of 2026-09-21 — RESUME HERE

This section supersedes § 0A where the two differ. Adam asked to proceed from
the [September 15 checkpoint](https://github.com/Adam-S-Daniel/skills-evals/pull/157#issuecomment-5685103205)
on 2026-09-21, from a Claude Code session on the Windows laptop driving the
WSL clone (`/home/passp/repos/skills-evals`; the Windows clone
`D:\repos\adam-s-daniel\skills-evals` has no Python and is used for `gh` only).

### PR #153: merged; first live proposal run verified

Adam authorized merges, releases and workflow dispatch in chat at about
14:35 UTC on 2026-09-21 and said he would be away for at least three hours.
[PR #153](https://github.com/Adam-S-Daniel/skills-evals/pull/153) merged at
14:37 UTC as merge commit
[`cddb224`](https://github.com/Adam-S-Daniel/skills-evals/commit/cddb224c464719d1a26212802b986ae31e3e941c)
(`--match-head-commit efb48b8`; parents `47bb7a9` and `efb48b8`; head and
merge both verified ancestors of `origin/main`). On the merge:
[CI](https://github.com/Adam-S-Daniel/skills-evals/actions/runs/35613393147)
and [Propagation](https://github.com/Adam-S-Daniel/skills-evals/actions/runs/35613393109)
success. The deferred final verification that preceded the merge is in the
[2026-09-21 checkpoint comment](https://github.com/Adam-S-Daniel/skills-evals/pull/153#issuecomment-5762059943):
generated multi-arm roster full suite **1446 / 2 skipped, exit 0**,
propagation **164 / 1 skipped**, sentinel run **1446 / 2 skipped** with one
nit filed as [#161](https://github.com/Adam-S-Daniel/skills-evals/issues/161).
The merge and live-run record is the
[next comment](https://github.com/Adam-S-Daniel/skills-evals/pull/153#issuecomment-5762476957).

[PR #129](https://github.com/Adam-S-Daniel/skills-evals/pull/129) is
superseded; GitHub marked it merged through `cddb224` because its head is
#153's base ([note](https://github.com/Adam-S-Daniel/skills-evals/pull/129#issuecomment-5762312946)).

**First real proposal run:**
[run 35613563071](https://github.com/Adam-S-Daniel/skills-evals/actions/runs/35613563071),
`workflow_dispatch` on `main` with the default fixture, every step success.
The eval ran on the committed roster; exhibit and badge published to
`eval-results` `9b6f3b5` (`previous_state: compared`, `proposal.status:
differs`, 16 changes, nothing retired); a valid proposal was pushed as one bot
commit [`c10df5d`](https://github.com/Adam-S-Daniel/skills-evals/commit/c10df5d333f86e3a65ea0fb807122f2f97fceea3)
on `roster/proposal` (parent `cddb224`, only `evals/roster.yml`); tracking
issue [#162](https://github.com/Adam-S-Daniel/skills-evals/issues/162)
carries the reasons and the compare link.

**Open decision for Adam, not blocking:** #162 proposes four arms
(`claude-haiku-4-5-20251001`, `claude-sonnet-5`, `claude-opus-5`,
`claude-fable-5-1`) and judge `claude-fable-5`, every seat by the
newest-per-tier fallback because **no usage census has ever been published**
(`usage/latest.json` is absent on `eval-results`; the census is step 6 of the
Tier-3 account-store Routine in `evals/propagation/ROUTINE.md` and needs a
transcript-bearing machine). It was not merged: it would multiply the paid
weekly run and raise the judge tier on no usage evidence, which is the human
call ADR 0001 reserves. Two ways forward: publish the census first so the next
Monday run proposes from usage, or open and merge a PR from `roster/proposal`
as is. The weekly run keeps proposing (and re-pushing `roster/proposal`) until
the committed file matches.

Local evidence: `.evals-resume-20260915/resume-20260921-final153/` on the WSL
workstation.

### Issue #152: merged as PR #163 (`47ca1e6`) after five review rounds

The branch was merged with `origin/main` `cddb224` as
[`fa9c788`](https://github.com/Adam-S-Daniel/skills-evals/commit/fa9c78830e2c940e5332d53912aa122915b38172)
(whitespace-only conflict) and opened as
[PR #163](https://github.com/Adam-S-Daniel/skills-evals/pull/163). Each
round had a fresh independent local reviewer on a read-only archive with
parse-only probes; each fix round was a local worker in the branch worktree,
pushed by the parent after release.

| Head | Review | Result |
|---|---|---|
| `fa9c788` | round 2 ([verdict](https://github.com/Adam-S-Daniel/skills-evals/pull/163#issuecomment-5763359157)) | all seven round-1 findings closed, merge clean; NOT CLEAN on six new should-fixes |
| [`4fefa14`](https://github.com/Adam-S-Daniel/skills-evals/commit/4fefa14faab2d42398fc247ec1fae758a4c13bed) (fix round 2, [record](https://github.com/Adam-S-Daniel/skills-evals/pull/163#issuecomment-5763979563)) | round 3 ([verdict](https://github.com/Adam-S-Daniel/skills-evals/pull/163#issuecomment-5764206754)) | six closed; NOT CLEAN on two **repeats** (sink preamble weaker than the helper rule; `shell` via `**kwargs`); **two-strikes fired**, decision 2 budget of three opened |
| [`a823fd8`](https://github.com/Adam-S-Daniel/skills-evals/commit/a823fd8891379c1421c37f36d7adc0e68a33e767) (fix round 3 = budget 1, [record](https://github.com/Adam-S-Daniel/skills-evals/pull/163#issuecomment-5764946603)) | round 4 ([verdict](https://github.com/Adam-S-Daniel/skills-evals/pull/163#issuecomment-5765213187)) | both closed, both declared scope bounds accepted; NOT CLEAN on one repeat (`from os import environ` not bound to the sentinel) |
| [`9bdcb95`](https://github.com/Adam-S-Daniel/skills-evals/commit/9bdcb954127739930f819223778cb50db125e472) (fix round 4 = budget 2, [record](https://github.com/Adam-S-Daniel/skills-evals/pull/163#issuecomment-5765974517)) | round 5 ([verdict](https://github.com/Adam-S-Daniel/skills-evals/pull/163#issuecomment-5766272464)) | **CLEAN**: 0 blockers, 0 should-fix, 3 nits, none a repeat |

Final head `9bdcb95`: full suite **1474 / 2 skipped, exit 0**, propagation
**164 / 1 skipped**, focused 41 and 40, CI `test`, `gate` and all five
propagation arms success. Merged at 19:28 UTC with
`gh pr merge --merge --match-head-commit 9bdcb95…` as merge commit
[`47ca1e6`](https://github.com/Adam-S-Daniel/skills-evals/commit/47ca1e69dfb6f5819d62b29773efd23369ff1599)
(parents `cddb224`, `9bdcb95`; both verified ancestors of `origin/main`).
Post-merge [CI](https://github.com/Adam-S-Daniel/skills-evals/actions/runs/35645037775)
and [Propagation](https://github.com/Adam-S-Daniel/skills-evals/actions/runs/35645037758)
on `47ca1e6` success. Issue #152 closed by the merge. The third budget round
was not needed. Both § 0A inspection questions were verified as real defects
in round 2 and closed in fix round 2.

What the scanner now holds and does not hold is in the docstring of
`test_every_suite_forking_test_in_this_repo_stands_down_in_a_child` in
`test/run_tests.py` on `main`. Documented out of scope: `functools.partial`,
`runpy.run_path` and `importlib.import_module` handoffs, an unparsed callee
not handed the environment mapping, an unresolvable argv name with no
shell/spread/string shape, an unparsed base class.

Follow-ups filed, both test-only, neither a regression:
[#161](https://github.com/Adam-S-Daniel/skills-evals/issues/161) (the
`#147` regression rows remove a pre-existing `roster/` in the checkout) and
[#164](https://github.com/Adam-S-Daniel/skills-evals/issues/164) (round-5
nits: unresolved mapping receivers and bound-method aliases in fixtures,
compound statements walked against pre-statement bindings, the docstring's
fixture claim). A single local worker was dispatched for both on a new
branch `claude/skills-evals-161-164` from `47ca1e6` (worktree
`.claude/worktrees/claude-161-164`); if this session ends before it lands,
its state is in `.evals-resume-20260915/fix161-164/` and the branch is
unpushed until reviewed.

Evidence directories under `.evals-resume-20260915/`:
`resume-20260921-i152-merge/`, `review152-round2/`, `fix152-round2/`,
`review152-round3/` (probes; verdict text is the PR comment),
`fix152-round3/`, `review152-round4/`, `fix152-round4/`,
`review152-round5/`, `fix161-164/`.

### Everything else

PR #124 in `_agent-guidance`, both fixture lanes, and the #139 receipt hold
are exactly as § 0A records them. The scheduled Monday eval on `main` keeps
running on the committed roster regardless of #153.

## 0A. Session of 2026-09-15 — RESUME HERE

This section supersedes the September 13 state below. Adam stopped this
continuation at a clean checkpoint after the account-wide weekly meter rose
from 22% at 15:49 UTC to 58% at 17:22 UTC. The remaining PR #153 merge and
first-live-run milestone was estimated to cost another 6–10 percentage points,
above his 5-point ceiling; completing and documenting this checkpoint was
estimated at 2–3 points. Likely resume next week in either Codex or Claude. Do not
launch another session automatically; resume when Adam requests it. Do not
repeat completed broad review without a new concern.

### Roster redesign: PR #153

[PR #153](https://github.com/Adam-S-Daniel/skills-evals/pull/153), branch
`claude/skills-evals-147`, is pushed, fetched, exact-SHA verified and clean at
`efb48b8849ffec0996348908aed80bf10994a3d7`. Its source worktree is
`skills-evals/.claude/worktrees/codex-reconcile-evals-20260915`, local branch
`codex/reconcile-evals-20260915`. All source and test-isolation fixes are done;
the worker released the clean tree with zero children. The
[latest public checkpoint](https://github.com/Adam-S-Daniel/skills-evals/pull/153#issuecomment-5684654811)
records the preceding round-three state and its single test-helper finding.

- The final test-only repair confines the proposal and results shell fixture
  to a disposable workspace. Its independent red/green proof reproduced the
  old caller-byte overwrite and confirmed the fixed helper preserves badge,
  roster and results bytes. Focused `TestIssue147` verification is **40 tests,
  exit 0**.
- The final code review is **CLEAN**, contingent on accepting the separate
  exact-head full verification. It found no new should-fix and did not repeat
  unchanged production review.
- Exact-head baseline: **1,446 tests, 2 skipped, exit 0** in 354.554 seconds;
  propagation: **164 tests, 1 skipped, exit 0** in 2.470 seconds. All archive
  manifests matched before and after at
  `ca4bb2ab1f09b6b0028738d83dc14f982478073320db6e23f001a1ceda83a434`;
  source manifests likewise matched at
  `22f0b114f83a1b612c5fe7a229d172cd0bffe1370950f347c4da6580d0be5e2b`.
  The local report is `final153-verification/REPORT.md`. Fixture parity from
  the earlier candidate remains 13 common skill fixtures and 98 checks per
  revision; it was not rerun because this final delta changes only the
  isolated test helper.
- The full generated multi-arm roster run and a bounded final adversarial
  confirmation of test isolation were deliberately deferred under the
  allowance stop. Earlier production adversarial coverage passed 11 tests
  plus 2 review checks; the previous NOT CLEAN verdict concerned only the now
  fixed test helper. Do not treat that earlier evidence as the missing final
  confirmation.
- No merge or live proposal dispatch occurred. Before merging, run the
  generated full suite and bounded adversarial confirmation, verify current
  PR CI plus legacy and `main` status surfaces, and accept the exact-head
  baseline and propagation evidence. Merge with a merge commit using the
  expected PR head, then verify the actual merge commit and its ancestry on
  `main`. Close [PR #129](https://github.com/Adam-S-Daniel/skills-evals/pull/129)
  as superseded, then dispatch and verify the first real proposal run.

### Suite-fork guard: issue #152

[Issue #152](https://github.com/Adam-S-Daniel/skills-evals/issues/152) is
pushed, fetched and exact-SHA verified at
`d6021b648724ac10aafa699c7b99b58d3e29d053` on branch
`codex/suite-fork-152-20260915` in
`skills-evals/.claude/worktrees/codex-suite-fork-152-20260915`. The first
published implementation, `d0b492148e946704aa0165720a1c28ef4b9fb841`, had a
NOT CLEAN review with seven findings, preserved in the
[public review checkpoint](https://github.com/Adam-S-Daniel/skills-evals/issues/152#issuecomment-5684502689).
The follow-up repairs the AST inventory, Python-target classification,
source-order binding, fail-closed guard proof and environment-marker precedence.
Its known inventory is 19 Python files, 42 explicit Python subprocess sites and
one generic sink; five suite-forking helpers are both discovered and verified.

- Final baseline: **1,195 tests, 2 skipped, exit 0**; propagation: **164
  tests, 1 skipped, exit 0**; focused checks: **21 tests, exit 0**. The repair
  also passed 26 actual-body mutation assertions, while three external mutants
  each failed their two-test runner with exit 1 as required. All 566-file
  manifests matched before and after. The local report is
  `fix152-round1/REPORT.md`.
- No fresh independent review or PR exists for the repaired candidate, and it
  has not been integrated with PR #153 or `main`. Resume those steps only after
  PR #153 merges. Read the final SHA before investigating two **unverified
  source-inspection questions**, which are not established defects: enclosing
  parameters may need to invalidate a same-named module constant before nested
  closures are collected; and a skip helper's side effects before it reads the
  child marker may defeat the guard proof. Do not execute a hostile helper
  mutant. Consolidate only reproduced findings in the next independent review
  before starting another fix cycle.
- Then continue [issue #139](https://github.com/Adam-S-Daniel/skills-evals/issues/139)
  under its existing receipt hold.

### InstructionsLoaded receipts: _agent-guidance PR #124

[_agent-guidance PR #124](https://github.com/Adam-S-Daniel/_agent-guidance/pull/124)
remains at `6e4d3b2`. Round 5 is **not clean**: the code reviewer reproduced a
fallback race that overwrites a newer unread receipt, and the claimed bounded
receipt read is followed by an unbounded reread that can still block if the
file changes type. Both independently prompted reviewers produced consistent
synthetic receipt measurements; the adversarial worker was then stopped by an
automated security filter before completing its review report. Its partial
measurements survive, but are not a completed review.

The code review's full suite reports **1,797 passed, 0 failed, exit 0**. The
old root-run count was 1,790: seven existing permission assertions run only
for a non-root user and all seven passed here, resolving the difference.
All three separate gates pass. The source branch was not changed, and it
also conflicts with current `main`.

The [round 5 checkpoint report](https://github.com/Adam-S-Daniel/_agent-guidance/pull/124#issuecomment-5683345936)
preserves both findings, their reproduction results, and verification limits.

This was the review after the last previously authorized fix round. Follow the
existing decision process before starting another fix round; do not silently
treat this handoff as an additional fix-round authorization.

### Local continuation pointers

Persistent session artifacts are under the local workspace's
`.evals-resume-20260915/`, including `CURRENT_SESSION.md`, briefs, verifier
logs, review reports and the allowance decision. These local files have no
public links. Temporary `/tmp` artifacts are not continuation records; keep new
evidence in the persistent workspace storage.

Inactive disarmed review archives from the PR #153 round-one code review and
the interrupted PR #124 base/head review were removed after their evidence was
preserved. The PR #153 cleanup was initially rejected by automatic review;
after all 389 files were proved identical to immutable archives, the repository
was confirmed clean and the profile directories empty, ordinary escalation
approved it and deletion succeeded. No real source worktree was removed or
changed. Both source workers released clean trees with zero test descendants;
no cleanup blocker remains.

- Candidate worktree: `skills-evals/.claude/worktrees/codex-reconcile-evals-20260915`,
  local branch `codex/reconcile-evals-20260915`.
- Issue #152 worktree: `skills-evals/.claude/worktrees/codex-suite-fork-152-20260915`,
  local branch `codex/suite-fork-152-20260915`.
- Handoff worktree: `skills-evals/.claude/worktrees/codex-handoff-evals-20260915`,
  branch `codex/handoff-evals-20260915`.
- Receipt source worktree: `_agent-guidance/.claude/worktrees/codex-resume-receipts-20260914`.

Portable resume sequence (Codex or Claude):

1. Read this Git-backed §0A and the
   [status board](https://github.com/Adam-S-Daniel/skills-evals/issues/126).
   If available, also read the local
   `/home/passp/repos/.evals-resume-20260915/CURRENT_SESSION.md`. Fetch the
   named remote refs and create dedicated worktrees when the listed local
   paths do not exist; then confirm their heads match this checkpoint.
2. From the PR #153 candidate worktree, run the generated multi-arm full suite
   in the already specified isolated archive environment, then perform the
   bounded final adversarial confirmation. Do not start another broad review
   unless new evidence creates a concern.
3. Read current PR #153 CI/check conclusions and `main`; merge only after every
   required condition above is green. Verify the merge commit, close PR #129,
   then dispatch and verify the first live proposal run.
4. Merge current `main` into the issue #152 branch, run only affected
   verification, obtain its first independent review, and open its PR.
   Continue #139 afterward. Leave PR #124 and both fixture lanes stopped.

## 0. Session of 2026-09-13 (superseded where § 0A differs)

Orchestrator session `session_01V1or9W61binLi5mFQXyKKR` (Fable 5.1), started
13:58 UTC under Adam's instruction to use the remaining weekly allowance
autonomously, then amended to tie off at 80–85% of the five-hour session
allowance for resumption on his new laptop in WSL. In-process subagents
(opus for harness work and one-way-door reviews, sonnet for mechanical fixes)
replaced the remote child sessions of earlier waves; everything they landed is
on pushed branches. The container's worktrees under `.claude/worktrees/` do
NOT survive; the branches do.

### Landed and merged

- **PR #151 → `main` `3fb20e1`** — closes #142 (hermetic sibling test), #143
  (`_read_matched` skips an unopenable file), #144 (`materialize_workspace`
  owns its mkdtemp). Suite on `main`: 1032 tests, exit 0.
  https://github.com/Adam-S-Daniel/skills-evals/pull/151

### Landed on branches, not merged

- **#129 / `claude/skills-evals-67` at `79b1ebe`** — decision 11 phase 1 done:
  `0db198a` reverted (`494091f`), the round-14 prose defects fixed
  (`1873a52`), two wall-clock tests made deterministic (`79b1ebe`; they had
  gone red on 09-10 with no code change). Suite 1320 tests, 2 skipped,
  1 expected failure (the pinned BLOCKER B survival), exit 0. BLOCKER 1
  reproduction: plant RETIRED, `judge.is_arm=False`, self-heals. Record:
  https://github.com/Adam-S-Daniel/skills-evals/pull/129#issuecomment-5653935006.
  This PR does not merge; it is the base of #147 and closes as superseded.
- **#147 / `claude/skills-evals-147`** — the redesign, under ADR
  `docs/decisions/0001-roster-trusted-on-main.md` (decision: the running
  roster is `evals/roster.yml` committed on `main`; `roster.py` computes a
  PROPOSAL from the committed history + live Models API + untrusted census;
  `eval.yml` pushes a differing proposal to bot branch `roster/proposal` and
  upserts a tracking issue; a human merges; the epicycles that approximated a
  trusted history are deleted). STATE: **LANDED at `6136234`,
  12 commits, PR [#153](https://github.com/Adam-S-Daniel/skills-evals/pull/153)
  open, NOT reviewed.** Suite 1286 tests exit 0 (−125 deleted with their
  mechanisms, +32 `TestIssue147` rows); the five #147 defects are regression
  rows RED on `424eebf` (spliced: 21 failures, 6 errors) and green on head;
  grep for every deleted name is zero outside `docs/decisions/`. It changes
  `eval.yml` (a proposal step, `issues: write`), so it needs the one-way-door
  review class before merge. **Rule 19 (fixture parity vs `main`) was NOT
  run** — run it first. The new step has never executed.
- **#138 — MERGED as `e4dfa41` (22:11 UTC) under Adam's option 2; #97
  closed.** The first two real `eval.yml` dispatches on `main` then both
  succeeded: `evals/workflow-path-audit`
  (https://github.com/Adam-S-Daniel/skills-evals/actions/runs/34786056328,
  `eval-results` `5893c66`) and `evals/guidance/_delivery`
  (https://github.com/Adam-S-Daniel/skills-evals/actions/runs/34786057436,
  `eval-results` `d83d407`: all five modes guard-ok and 1/1, delivery `user`,
  so the pinned CLI does read memory from `CLAUDE_CONFIG_DIR`). #152 (the
  fork pin) is the follow-up. What follows is the pre-merge record.
  `claude/skills-evals-97` at `3c558a5` was fix round 4 (`b583341`)
  + merges of `main` `1530b51` and `3fb20e1` + one reconciliation commit.
  Suite 1184 exit 0; CI `test` success on the head. Round 5 (deciding, both
  halves, ref `f9115ce`): **NOT CLEAN on both
  halves, no blocker, ONE shared should-fix** — the suite-fork pin's
  membership scan (fourth return of round-2's S-B), filed as
  [#152](https://github.com/Adam-S-Daniel/skills-evals/issues/152). Everything
  else (all seven round-4 items, the merge union, the two allowlists under a
  hostile parent, the one-way door and the rewritten security header) is
  certified closed by both halves. Fix budget spent → **PARKED ON ADAM** with
  three options, recommendation option 2 (merge as is; #152 follow-up):
  https://github.com/Adam-S-Daniel/skills-evals/pull/138#issuecomment-5655302421
  Record: https://github.com/Adam-S-Daniel/skills-evals/pull/138#issuecomment-5654171687
- **_agent-guidance #124 / `claude/agent-guidance-123`** — round 4 on
  `8ec4cb3` NOT CLEAN both halves, no blocker, three should-fixes shared by
  both halves (FIFO at the receipt read hangs `fleet-memory.sh`;
  `restore_receipt` conflates EEXIST with no-hardlinks; a `.claude` symlink
  makes the sync write outside the clone). Record:
  https://github.com/Adam-S-Daniel/_agent-guidance/pull/124#issuecomment-5654086790.
  Fix round 4 (the LAST of three): **LANDED at `6e4d3b2`** (four
  commits: S1 `068ff45`, S2 `a98fdd2`, S3 `c5434ae`, nits `6e4d3b2`); suite
  1790 passed / 0 failed, three gates exit 0, `.github/` byte-unchanged. Round
  5 (both halves) NOT run this session. Record:
  https://github.com/Adam-S-Daniel/_agent-guidance/pull/124 (the 2026-09-13
  comments).

### Facts learned this session

- **The propagation `gate` is red on every PR and every scheduled `main`
  run since 2026-09-09** because the account-store audit Routine
  (`skills-evals: account-store propagation audit (sourced binding)`,
  `trig_01AK5s6efLSzdHBSZhkx6KW1`) is DISABLED with no `ended_reason` — paused
  by hand around the 09-06 pause. `eval-results` carries nothing newer than
  `c35c57b` (09-06). Re-enabling it is Adam's call (it spends the allowance
  daily); `gate` is not a required context, so merges proceeded on a green
  `test` with a standing-down comment each time. **RESOLVED 19:44 UTC:** Adam
  re-ran the Routine; `eval-results` `e94b25d` carries a fresh `pass` artifact,
  so the gate reads green from the next run. Nothing is waiting on him here.
- **Two roster tests read the wall clock** through `roster.main()` (fixed on
  the #67 branch). Any test that drives `roster.py` without a frozen `now`
  and a hard-coded `created_at` will do the same; build dates relative to now.
- **`git remote remove origin` inside a worktree strips the PARENT's remote**
  — a worker did it and restored it; the fleet guidance already says so.
- **The five-hour rate limit kills in-process subagents mid-tool-call** with
  no report; their transcripts persist and `SendMessage` to the agent id
  resumes them with context intact. It fired once this session at ~15:46 UTC
  after ~1h50m with four to five opus agents running.
- Session cost read from `get_session`: $220.58 at 18:04 UTC, **$358.03 at
  19:05 UTC** (the tie-off), for everything this session and its subagents did.

### Adam's decisions this session

12. 2026-09-13: use the remaining weekly allowance autonomously on the
    handoff, starting from the #129 estimate comment if sensible.
13. Same day, later: tie off at 80–85% of the five-hour session allowance for
    resumption on the new laptop in WSL.

### Resume on the new laptop (WSL)

1. Clone side by side (the suite resolves siblings at `REPO_ROOT/..`):
   `skills-evals`, `_agent-guidance`, `agentskills`. #142 is fixed, so a
   side-by-side layout no longer reds `main`.
2. Toolchain: `python3 -m pip install --user markdown-it-py==4.2.0`; mikefarah
   `yq` v4.53.3 FIRST on `PATH` for `_agent-guidance` (the distro `yq` is the
   wrong tool); `npm ci --ignore-scripts` in `_agent-guidance`. Run every
   suite with a throwaway `HOME` and `SKILLS_EVALS_USER_MEMORY`
   (`CLAUDE_CONFIG_DIR` for `_agent-guidance`).
3. Verifiers: skills-evals `python3 test/run_tests.py` (exit 0; counts above)
   and `python3 test/test_propagation.py` (164); _agent-guidance
   `./test/run-tests.sh` plus the three gates.
4. Next commands, in order: 
   - **#153 (#147):** Rule 19 on `6136234` against `main`; then round 1, code
     + adversarial (one-way-door: `eval.yml`), hollowness vs `79b1ebe`; CLEAN
     → merge with a merge commit → close #129 as superseded → the first real
     `eval.yml` dispatch on `main` (it exercises the proposal step for the
     first time). Watch that run by conclusion.
   - **#138:** DONE — merged, both first real dispatches green (above).
     Next in that lane: #139 (the InstructionsLoaded receipt uses), then the
     harness lane order below.
   - **_agent-guidance #124:** round 5, both halves, on `6e4d3b2` (the
     `sync.yml` door unchanged, read against the security header anyway).
     CLEAN → merge → read the `sync.yml` run by conclusion → close #123.
   - **#152:** the fork-pin redesign, a bounded test-only change; can ride
     #138 option 1 or stand alone.
   - Then the harness lane in HANDOFF § 2 order (#139, #66, #64, …).
5. The review prompts and reports of this session are NOT on the snapshot
   branch (no push of `.orchestration/` was made); the PR comments linked
   above carry the verdicts and findings.

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
| [#129](https://github.com/Adam-S-Daniel/skills-evals/pull/129) (#67) | one more fix round scoped to the adversarial fix list; round 13 decides | Round 13 NOT CLEAN, parked on [that comment](https://github.com/Adam-S-Daniel/skills-evals/pull/129#issuecomment-5589817444)'s four options. Answered "1" a second time; **round 14 ran and was NOT CLEAN too**, and decision 11 ends the fix-round approach. See below. |

**Answering a park comment with option 1 carried that PR to a merge; it did not
reopen epic #62 or #96.** Nothing else in either lane was dispatched, and the
real N=3 runs owed for the now-eight merged skill fixtures are still not
pursued. #81 and #84 stay OPEN as "merged hermetic; real run stopped".

#### #129's state, precisely (this is where a resuming session starts)

Branch `claude/skills-evals-67` at **`424eebf`**, pushed, **suite green — 1321
tests exit 0, 2 skipped**, run by the orchestrator in the real worktree with
`harness/roster.py`, `test/run_tests.py`, `evals/roster-policy.yml` and
`DESIGN.md` md5'd before the run and re-checked `OK` after it, so the green
measures the tree it claims to. Mergeable against `main`; `.github/` byte-
unchanged since `7ef5780`, which carries round 13's one-way-door read forward
without re-doing it.

**It is NOT merged and should not be merged as it stands.** Decision 11:
`git revert 0db198a` first, then the redesign under
[#147](https://github.com/Adam-S-Daniel/skills-evals/issues/147).

**Nothing is blocked by not merging it.** `eval.yml` on `main` dispatches exactly
one fixture, `evals/workflow-path-audit`, which pins both `model:` and
`judge.model:`, and its `workflow_dispatch` carries no inputs — verified in round
13 and again in round 14. So a real dispatch does not fail closed today whether
or not #129 lands.

**Round 14** (fix worker opus; both review halves opus at high) ran on
`87f2031` = `d84c1c8` + a merge of `origin/main`, and produced six commits
`54daf66..424eebf`. Verdicts: adversarial `FOUND — 3 blocker, 3 should-fix,
3 nit`, PARK; code `FOUND — 1 blocker, 3 should-fix, 3 nit`, PARK — every one of
the code half's findings comment or docstring text, none a code or assertion
change, and its own summary was that *"the mechanism half is done and
independently verified ... I could not construct an input that retires a live
arm."* The full evidence is the
[round-14 park comment](https://github.com/Adam-S-Daniel/skills-evals/pull/129#issuecomment-5591678318).

**What round 14 genuinely closed, and it is not nothing.** BLOCKER A: the
`anchored_held >= bar` conjunct is deleted and the veto is round 12's prescribed
fraction-alone rule, so the park comment's own measurement — a true 94.3%
published `RETIRED ... (1.2%)` from one added `arms` line — now reads as a
refused retirement. ITEM 4 doubled the class floor for real, confirmed
independently by both halves: head's tests against base `harness/roster.py` fail
rows 1, 2 and 11 **and only under `victim_shape='fold-reached'`**. ITEM 5's
figures reproduce byte-for-byte (`1590 / 1535 / 150 / 73 (49%) / 77 / 1`) and now
ship as a re-runnable command, `python3 test/run_tests.py
--measure-previous-only-distribution`, rather than a number in a comment. The
`_usage_alias_map` split into `_usage_alias_hops` + `_compose_alias_chains` is
behaviour-preserving over 20,000 randomised trials with invariants (i)/(ii)
clean and (iii) clean over 5,417 trials. The dropped `relevant.is_live()`
conjunct is genuinely dead: 4,000 fuzzed `compute_roster` calls reached that sink
1,227 times with zero violations.

**BLOCKER 1 is a REGRESSION round 14 introduced, and the round-14 brief caused
it.** The brief stated ITEM 2's invariant as "no live catalogue id is ever
retired on a numerator of zero" and missed that a *planted* `arms` entry for an
unused live model IS a zero-numerator live arm. The worker implemented that at
the sink with the cost stated; the cost statement is narrower than the cost.
Reproduced by the orchestrator on both heads — four live models, an honest fully
attributable census, one added `arms` line naming the one live model with no
usage:

```
                          base 87f2031                    head 424eebf
one planted arms line     plant RETIRED same run          plant HELD OVER
judge                     claude-haiku-4-5 is_arm=False   claude-opus-7 is_arm=TRUE
runs 2-3, plant reverted  self-heals                      persists
```

`run_eval.select_models` refuses every unpinned fixture when `judge.is_arm` is
true, and the arm set is republished as this run's own output — so one line on
the untrusted branch permanently halts the harness for unpinned fixtures and
reverting the line does not undo it. The rule is non-monotonic in the direction
that matters: a model used *once* in 10,001 turns is retired, a model used *not
at all* is immortal. **`0db198a` is the sole cause and reverting it is decision
11's first step.**

**The obvious repair was tested and does not hold.** Narrowing the refusal to
require ranked-but-unattributable in-window turns — positive evidence of a broken
chain rather than absence of evidence — does separate BLOCKER B's victim from the
plant, but the census lives on the same untrusted branch, so one extra planted
census key carrying a family word restores the plant's immunity. It raises the
attack from one line to two; it does not close it. Do not re-derive this.

**BLOCKERS 2 and 3 are survivals, measured byte-identical on both heads.**
(2) `is_needed_hop` asks whether a chain needs an id in *this* run's census, but
eviction is permanent and a kept hop's `last_seen` is never refreshed — so one
quiet window ages the bridge out for good and the next busy window retires a live
arm carrying a true 23.9% at 0.1%, rc 0, empty stderr, permanently, with **no
hostile input at all** (run 2's `previous.json` is run 1's own output).
Reproduced at bridge ages 181/200/365/400 days; the 179-day control does not
fire. (3) = round 13's BLOCKER C, untouched: `is_needed_hop` walks *forward* from
census keys, so it covers an entry that is a **hop** and not one that is the fold
**source** — the documented B1'/round-10 shape, a model observed under a DATED id
whose census usage is recorded under the UNDATED alias. `tier()` misses it (raw
identity), `is_needed_hop` misses it (wrong direction). One `last_seen` date, and
9,500 real turns leave the denominator permanently: a hold-over becomes a seat at
`carries 100.0%` on a true 5.0%. No planter needed — the date is what this
harness itself wrote.

**Prose defects both halves found, and one the orchestrator found first.**
`harness/roster.py:2629-2657` — the comment block *governing the branch round 14
rewrote* — still describes the deleted conjunction, including *"It is not a
permanent block: the arm still retires once its own usage falls away"*, which the
`held == 0.0` branch twelve lines below makes false. The tree already records
this exact failure once, as round 12's should-fix 1, in the same function. Also
`:2917-2920`, `:844` (`_format_share`'s "no caller can reach" clause, falsified
by round 14's own new call site) and `test/run_tests.py:28502`. And the
anchor-tolerance veto is structurally blind to the **deletion** direction —
removing entries shrinks `previous_only` toward zero — which nothing in the `#:`
block says.

**Why fourteen rounds have not closed this, in one sentence.** *Every surviving
defect is the same defect: `previous.json` and the census both live on
`eval-results`, which the design treats as untrusted, and the harness keeps no
second copy of what it has observed — so "this id was never an arm" and "the
record was tampered with" are the same input, as are "this model is unused" and
"its chain is broken".* Each round has keyed a sharper local check on something
an adversary can vary — raw identity, then an exact zero, then this run's census,
then one direction of the fold. BLOCKER 1 is the sharpest evidence: the remedy
for a silent destruction produced a permanent halt, because both readings of a
zero are one untrusted line away. **A round 15 of the same shape is not
recommended and was not authorised.**

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
  #122, #65, #98 (in that order). #67 is no longer a fix-round item: its PR
  parks at `424eebf` and the work moves to
  [#147](https://github.com/Adam-S-Daniel/skills-evals/issues/147), the trusted-
  history redesign, which is where BLOCKERS 1, 2 and 3, round 13's BLOCKER B and
  the declared open cell all close together.
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
    every relevant issue and PR on the way out. Outcome: #131 and #130 merged,
    #129 parked again on a NOT CLEAN round 13, spend about $140 (68% of the
    line).
11. 2026-09-08, after round 13's park: "Finish #129 using no more than **4% of
    the weekly tokens**" — read as option 1 (a fix round scoped to the fold
    relation, then round 14 decides), since it is the only option that ends with
    the PR landed and it fits the line. Round 14 ran and was NOT CLEAN on both
    halves, with one blocker a REGRESSION the round introduced. Adam then took
    the orchestrator's recommendation verbatim: **option 4 — redesign the
    denominator around a trusted history
    ([#147](https://github.com/Adam-S-Daniel/skills-evals/issues/147)) — with
    `git revert 0db198a` done FIRST so the branch carries no regression.** The
    next session is to open with an ESTIMATE RANGE, in percentage points of the
    weekly limit, and await approval before doing any work.

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
