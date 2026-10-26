## Repo-specific additions

<!-- Add your repo-specific agent guidance below this line -->

- **Evals programme handoff.** Read [`HANDOFF.md`](HANDOFF.md) first: the whole
  systematic-evals effort (skills and fleet guidance, six epics), where it
  stands, what is parked on Adam and why, and how to resume it. The live
  operational state is the status board,
  [skills-evals#126](https://github.com/Adam-S-Daniel/skills-evals/issues/126).

- **Running tests in a fresh or cloud session.** Run `bash scripts/dev_setup.sh`
  first: it installs what `ci.yml`'s `test` job installs (the pip pins and the
  four fixture `npm ci` directories), and `test/issues/test_issue_dev_setup.py`
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

- **Workflow triggers and salient paths.** `test` (ci.yml) is the one
  required check. Keep this table in step when a trigger or filter moves.

  | Workflow | Triggers | Salient-path handling |
  |---|---|---|
  | `ci.yml` | `pull_request`, `push` to main, dispatch | `pull_request` unfiltered (required check); step `salient` gates the suite on `SALIENT_PATHS`, which must equal `on.push.paths` (`CiDispatchTests`) and includes `.github/workflows/actions.lock`, `.github/workflows/**` and `.github/actions/**` |
  | `propagation.yml` | `pull_request`, `push` to main, schedule, dispatch | deliberately unfiltered: it probes an unpinned upstream registry (its header says why). `coverage` is informational and not required: absent optional registry access makes its census unresolved without testing a PR, so PR/push/dispatch record a warning while schedule fails. Only `coverage-publish` on schedule writes `persistent/eval-results`; the optional private checkout uses a token minted from the read-only registry GitHub App (variable `REGISTRY_READ_APP_CLIENT_ID`, secret `REGISTRY_READ_APP_PEM`) in that checkout step alone. |
  | `dependabot-auto-merge.yml` | `pull_request`, schedule, dispatch | acts only on Dependabot PRs whose changes stay inside the manifest-path allowlist |
  | `eval.yml` | dispatch only | no push or PR trigger; Adam's 2026-10-06 decision retired its Tuesday schedule because the [weekly routine](https://github.com/Adam-S-Daniel/skills-evals/pull/331) replaces it |
  | `roster-refresh.yml` | schedule, dispatch | no push or PR trigger, so no path filter; dispatches eval.yml with roster_only=true weekly so the roster follows current use |
  | `scheduled-run-health.yml` | schedule, dispatch | no push or PR trigger, so no path filter |
  | `routine-eval-fire.yml` | dispatch only | none needed |
  | `routine-eval-weekly.yml` | schedule only | no push or PR trigger; replaces `eval.yml`'s Tuesday schedule per Adam's 2026-10-06 decision; plans the reviewed fixture list and dispatches eval mode through `routine-eval-fire.yml` |
  | `routine-eval-results-pushed.yml` | `push` to `claude/eval-*` | `paths: eval-results/**` (the routine's pinned result root); holds no permissions and runs nothing from the branch |
  | `routine-eval-ingest.yml` | `workflow_run` of the above, dispatch | runs the default branch's copy only; `scripts/ingest_routine_results.py` validates the branch and writes `persistent/eval-results` `routine-results/<run id>/` (ADR 0010 decision 2) |
  | `routine-improve-pushed.yml` | `push` to `claude/eval-improve-*` | `paths: eval-improve/**` (the one directory an improve branch adds to; disjoint from `eval-results/**`, which is what keeps it off the results ingest); holds no permissions and runs nothing from the branch |
  | `routine-improve-gate.yml` | `workflow_run` of the above, dispatch | runs the default branch's copy only; `scripts/improve_gate.py` validates the branch without running it, then a draft PR in adam-agentskills is opened with a GitHub App token, minted only when secrets `EVAL_IMPROVE_APP_CLIENT_ID` and `EVAL_IMPROVE_APP_PEM` both exist; never merges (ADR 0005, routine improve mode addendum) |
  | `routine-scaffold-pushed.yml` | `push` to `claude/scaffold-*` | `paths: evals/real-work/**` (the one directory a scaffold adds to); holds no permissions and runs nothing from the branch |
  | `routine-scaffold-gate.yml` | `workflow_run` of the above, dispatch | runs the default branch's copy only; `scripts/scaffold_real_work.py gate` validates the branch without running it, then a second job opens a draft PR labeled `eval-scaffold` (never merges; DESIGN.md "The scaffolder and its gate") |
  | `routine-draft-skill.yml` | daily schedule, dispatch | no push or PR trigger, so no path filter; picks one `new-skill` lesson from adam-agentskills-private's `lessons/` on `persistent/lessons` (read-only registry App token), skipping drafted subjects and existing skills, re-admitting subjects whose hook proposal was closed as not planned, and dispatches draft mode through `routine-eval-fire.yml` when one fire fits the weekly allowance |
  | `routine-draft-skill-pushed.yml` | `push` to `claude/draft-skill-*` | `paths: draft-skill/**, evals/**` (the two directories a draft branch adds to; no other routine signal matches the branch); holds no permissions and runs nothing from the branch |
  | `routine-draft-skill-gate.yml` | `workflow_run` of the above, dispatch | runs the default branch's copy only; `scripts/draft_new_skill.py validate` judges the branch without running it; hook-first opens a `Hook proposal: <subject>` issue (job token, `issues: write`); accepted opens a draft skill PR in adam-agentskills (App token, as the improve gate) and then a draft fixtures PR here (job token, `contents: write`); never merges |
  | `skill-coverage.yml` | daily schedule, dispatch | no push or PR trigger; reads all four registries for a redacted census, publishes on schedule or explicit non-dry dispatch, and proposes up to three public GAP drafts; its `retirement` job runs on schedule only, computes the #70 verdicts from `persistent/eval-results` and files or updates a retirement issue (`issues: write`, `--allow-mode proposal`) |

### Action pins

Workflows name third-party actions by release tag; [`.github/workflows/actions.lock`](.github/workflows/actions.lock) locks each tag to an exact commit, and the runner runs the locked commit even when it disagrees with the tag. The `test` job's "Verify action lockfile" step is the shared action [`Adam-S-Daniel/verify-actions-lock`](https://github.com/Adam-S-Daniel/verify-actions-lock); it runs `gh actions-lock --verify` only when a PR touches workflow dependencies (`.github/workflows/**`, `.github/actions/**`, an `action.yml`/`action.yaml`) and fails on any finding except `cooldown-config-ignored` (dependabot.yml's cooldown `exclude`, which the tool ignores). It is early feedback, not the only guard: the runner rejects forged pins, and the repo will also turn on GitHub's Require lockfile policy. Write the exact tag by hand, regenerate with `gh actions-lock --no-narrow`, and commit both files; review an `actions.lock` diff as you would a SHA pin. A stale or moved pin is fixed with `gh actions-lock --accept-moved`; review the diff. A `reachability-unknown` failure means the GitHub API was unreachable: re-run. Cross-repo reusable workflows (`jobs.<id>.uses`) are not locked, so they take a full commit SHA (`Adam-S-Daniel/cms-platform` refs excepted); a test enforces it. Fleet rule: [ADR 0024](https://github.com/Adam-S-Daniel/_agent-guidance/blob/main/docs/decisions/0024-actions-pin-through-lockfiles.md).
