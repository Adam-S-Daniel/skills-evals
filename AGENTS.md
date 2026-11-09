<!-- BEGIN MANAGED SECTION — DO NOT EDIT ABOVE "## Repo-specific additions" -->
<!-- Source: _agent-guidance -->
<!-- Sections: none -->
<!-- Mode: stub -->

# AGENTS.md

> **Managed by [`_agent-guidance`].**
> Edit only below the `## Repo-specific additions` header.
> Everything above it will be overwritten on the next sync.

guidance-marker: fleet-stub (transcript counts use this line; keep it)

## Fleet guidance is delivered once per session — not by this file

The full guidance, floor rules included, is installed into user memory by
the `fleet-memory` SessionStart hook, whose verdict line says whether it
loaded. `installed` or `current`: it is in context. `DEGRADED` or no verdict:
it is not, so read [`agents-md/base.md`](https://github.com/Adam-S-Daniel/_agent-guidance/blob/main/agents-md/base.md)
before non-trivial work and say you ran degraded. `skipped`: read it too, but
it is the owner's choice, so do not report or "fix" it. Always, and above all
before you have read it: never push to a default branch, force-push a shared
branch, commit a secret, or print personal data to a CI log. Keep this file
under 32 KiB (Codex silently truncates it).

**Your first reply to the user in a session begins**
`fleet-guidance check: <value>`, copied from the installed guidance's
`fleet-guidance check value:` line, or `fleet-guidance check: none` when no
such line is in your context. Never guess one or copy it from a file you
read; only in replies to the user.

<!-- END MANAGED SECTION -->
## Repo-specific additions

<!-- Add your repo-specific agent guidance below this line -->

- **Evals programme handoff.** Read [`HANDOFF.md`](HANDOFF.md) first: the whole
  systematic-evals effort (skills and fleet guidance, six epics), where it
  stands, what is parked on Adam and why, and how to resume it. The live
  operational state is HANDOFF.md's "Current state" section. The old status
  board, [skills-evals#126](https://github.com/Adam-S-Daniel/skills-evals/issues/126),
  is closed and not updated.

- **Running tests in a fresh or cloud session.** Run `bash scripts/dev_setup.sh`
  first: it installs what `ci.yml`'s `test` job installs (the pip pins, the fixture
  `npm ci` directories and the fixtures' Ruby gems via `bundle install`), and `test/issues/test_issue_dev_setup.py`
  keeps the two in step. Then run the module that covers your change,
  `python3 -m pytest test/issues/<file>.py -q -n 2`, and report its count
  beside its exit code. `python3 -m unittest test.issues.<name>` cannot import
  (`test/` is not a package). The full suite,
  `python3 test/run_tests.py --jobs auto`, did not finish inside a 10-minute
  foreground command limit on 2 cores (2026-10-10), so start it in the
  background with its output in a log and poll, or let CI's `test` be the
  record. A cloud container has no `bwrap`, so tests of workspace-executing
  scorers fail closed there. Wrap any run in
  `unshare --user --map-current-user --pid --fork --mount-proc --`.

- **`tool/index.html` is built from `explorer/src`**: edit there, run
  `npm run build` in `explorer/`, commit both; CI fails on drift.

- **A new `evals/<skill>/` directory needs a line in `README.md`'s layout
  block** in the same commit. `test_every_eval_directory_is_named_in_the_readmes_layout`
  (`test/run_tests.py`) fails CI otherwise.

- **Guidance loop merges wait for _agent-guidance's weekly window** (Monday
  17:00 to 19:00 UTC; the bounds live only in its
  `scripts/base-md-merge-window.yml`; [ADR 0017](docs/decisions/0017-guidance-loop-merges-wait-for-the-weekly-window.md)).
  Outside it the improvement gate queues its pull request unarmed and
  `guidance-merge-window.yml` arms it on Mondays; `retire_skill.py --target
  guidance` opens no removal. A new path that merges `agents-md/` changes by
  automation must ask `scripts/guidance_merge_window.py` first. A manual merge
  outside the window restarts every guidance section's eval evidence.

- **Workflow triggers and salient paths.** `test` (ci.yml) is the one
  required check. Every workflow's triggers and salient-path handling are
  tabled in [`docs/workflows.md`](docs/workflows.md); keep that table in step
  when a trigger or filter moves.

### Action pins

Workflows name third-party actions by release tag; [`.github/workflows/actions.lock`](.github/workflows/actions.lock) locks each tag to an exact commit, and the runner runs the locked commit even when it disagrees with the tag. The `test` job's "Verify action lockfile" step is the shared action [`Adam-S-Daniel/verify-actions-lock`](https://github.com/Adam-S-Daniel/verify-actions-lock); it runs `gh actions-lock --verify` only when a PR touches workflow dependencies (`.github/workflows/**`, `.github/actions/**`, an `action.yml`/`action.yaml`) and fails on any finding except `cooldown-config-ignored` (dependabot.yml's cooldown `exclude`, which the tool ignores). The runner also rejects forged pins, and GitHub's Require lockfile policy is on. Write the exact tag by hand, regenerate with `gh actions-lock --no-narrow`, and commit both files; review an `actions.lock` diff as you would a SHA pin. A stale or moved pin is fixed with `gh actions-lock --accept-moved`; review the diff. `reachability-unknown` means the API was unreachable: re-run. Cross-repo reusable workflows (`jobs.<id>.uses`) are not locked, so they take a full commit SHA (`Adam-S-Daniel/cms-platform` refs excepted); a test enforces it. Fleet rule: [ADR 0024](https://github.com/Adam-S-Daniel/_agent-guidance/blob/main/docs/decisions/0024-actions-pin-through-lockfiles.md).
