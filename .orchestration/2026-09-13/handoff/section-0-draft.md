## 0. Session of 2026-09-13 — RESUME HERE (supersedes § 7 where they differ)

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
  trusted history are deleted). STATE: __147_STATE__
- **#138 / `claude/skills-evals-97` at `3c558a5`** — fix round 4 (`b583341`)
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
  Fix round 4 (the LAST of three): __124_FIX4__

### Facts learned this session

- **The propagation `gate` is red on every PR and every scheduled `main`
  run since 2026-09-09** because the account-store audit Routine
  (`skills-evals: account-store propagation audit (sourced binding)`,
  `trig_01AK5s6efLSzdHBSZhkx6KW1`) is DISABLED with no `ended_reason` — paused
  by hand around the 09-06 pause. `eval-results` carries nothing newer than
  `c35c57b` (09-06). Re-enabling it is Adam's call (it spends the allowance
  daily); `gate` is not a required context, so merges proceeded on a green
  `test` with a standing-down comment each time.
- **Two roster tests read the wall clock** through `roster.main()` (fixed on
  the #67 branch). Any test that drives `roster.py` without a frozen `now`
  and a hard-coded `created_at` will do the same; build dates relative to now.
- **`git remote remove origin` inside a worktree strips the PARENT's remote**
  — a worker did it and restored it; the fleet guidance already says so.
- **The five-hour rate limit kills in-process subagents mid-tool-call** with
  no report; their transcripts persist and `SendMessage` to the agent id
  resumes them with context intact. It fired once this session at ~15:46 UTC
  after ~1h50m with four to five opus agents running.
- Session cost read from `get_session` at 18:04 UTC: $220.58.

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
4. Next commands, in order: __NEXT__
5. The review prompts and reports of this session are NOT on the snapshot
   branch (no push of `.orchestration/` was made); the PR comments linked
   above carry the verdicts and findings.
