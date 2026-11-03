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

The account's full guidance — incidents, fleet policy, machine layout, the
traps that cost real outages — is installed into **user memory**
(`~/.claude/CLAUDE.md`) by the `fleet-memory` SessionStart hook, so it is
loaded **once per session** no matter how many repos are attached
([inlined per repo, it took 332.3k tokens](https://github.com/Adam-S-Daniel/_agent-guidance/blob/main/docs/evidence/2026-08-29-guidance-inlined-in-every-repo.md)).

**Check the session-start verdict before you rely on it.** The hook prints one
line:

- `fleet-guidance: installed (v<id>, <n> bytes)` or `fleet-guidance: current` —
  the full guidance is in context. Use it.
- `fleet-guidance: DEGRADED — <reason>` — it is **not** in context. You have
  only what is below. Read `agents-md/base.md` in the `_agent-guidance`
  checkout (or on GitHub) before non-trivial work, and say in your reply that
  you were running degraded.
- `fleet-guidance: skipped (FLEET_GUIDANCE_SKIP set)` — also not in context,
  but by the machine owner's deliberate choice, not a fault. User memory is
  GLOBAL on a durable machine, so the guidance would otherwise load in every
  unrelated project on that box; `FLEET_GUIDANCE_SKIP` opts out and removes any
  block an earlier session installed. Read `agents-md/base.md` the same way you
  would when degraded — just don't report it as a problem or try to "fix" it.

No verdict at all means the hook never ran — treat that as DEGRADED.

**Say what loaded, in your first reply to the user in a session.** The
installed guidance ends with a line `fleet-guidance check value: <8 hex>`.
Begin that reply with `fleet-guidance check: <the value>`, copied from that
line, or `fleet-guidance check: none` when no such line is in your context.
Never guess a value or copy one from anywhere else: the session's record
compares it with what actually loaded. Only in replies to the user — never in
commits, PR or issue text, files or prompts for other agents.

## Codex reads the same block, from `~/.codex/AGENTS.md`

The hook writes the same block there whenever `~/.codex` exists. Setup for
local Codex and Codex Cloud, and how to verify delivery:
[`docs/codex-cloud.md`](https://github.com/Adam-S-Daniel/_agent-guidance/blob/main/docs/codex-cloud.md).

## The floor: rules that hold even when the guidance did not load

These are the ones with teeth. They are restated here, deliberately, because a
session that lost the guidance must not also lose these.

- **Branch protection is real.** Fleet repos are PR-only on their default
  branch; a direct push is rejected (GH013), even from the repo's own
  workflows. Never design a bot that pushes to a protected default branch.
- **Every `uses:` is pinned through `.github/workflows/actions.lock`: an
  exact tag, locked, checked by a required `gh actions-lock --verify`
  failing on any pin finding.** A repo not yet migrated keeps the legacy
  form, a full 40-character commit SHA with no trailing version comment,
  until its migration PR; never mix the two in one repo. Cross-repo
  reusable workflows take a full SHA either way. The one carve-out is a ref
  into this account's own `cms-platform`, which stays on its release tag.
- **Never commit secrets or `.env` files, and never print personal data to a
  CI log** — logs, artifacts and git history on a public repo are public.
- **A successful `git push` does not mean your commit exists.** A refused
  pre-commit hook still lets the push report success. Verify with
  `git merge-base --is-ancestor <sha> origin/<branch>` — it is the only check
  that names both the commit and the ref.
- **"The watch finished" is not "CI passed."** Read the parsed conclusions;
  never infer pass/fail from a watch command's exit code.
- **A GitHub 404 means "not authorized", not "not there."** Never report a
  repo, PR or branch as gone on a 404 alone.
- **The fleet spans TWO owners** — `Adam-S-Daniel` and `jodidaniel`. A query
  scoped to one returns a plausible, complete-shaped, wrong answer.
- **Anything you name gets its link** — what you hand over, what you are
  waiting on, and what you cite as already done.
- **Merge with a merge commit** (`gh pr merge --merge`), except in the three
  cms-platform-managed repos (`cms-platform`, `adamdaniel.ai`,
  `jodidaniel.com`), which squash; do not amend published commits or
  force-push shared branches.
- **Keep this file under 32 KiB.** Codex truncates project instructions at
  that byte silently; the sync warns and the drift report flags
  `codex-truncated`.

<!-- END MANAGED SECTION -->
## Repo-specific additions

<!-- Add your repo-specific agent guidance below this line -->

- **Evals programme handoff.** Read [`HANDOFF.md`](HANDOFF.md) first: the whole
  systematic-evals effort (skills and fleet guidance, six epics), where it
  stands, what is parked on Adam and why, and how to resume it. The live
  operational state is the status board,
  [skills-evals#126](https://github.com/Adam-S-Daniel/skills-evals/issues/126).

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

- **Workflow triggers and salient paths.** `test` (ci.yml) is the one
  required check. Keep this table in step when a trigger or filter moves.

  | Workflow | Triggers | Salient-path handling |
  |---|---|---|
  | `ci.yml` | `pull_request`, `push` to main, dispatch | `pull_request` unfiltered (required check); step `salient` gates the suite on `SALIENT_PATHS`, which must equal `on.push.paths` (`CiDispatchTests`) and includes `.github/workflows/actions.lock`, `.github/workflows/**` and `.github/actions/**`. The suite runs as a `suite` matrix of shards (`run_tests.py --shard K/N`, split by `test/shard.py`); the required `test` job passes only when every shard succeeded (`CiShardTests`) |
  | `agent-checks.yml` | `pull_request`, `push` to main/master, dispatch | none: the `pull_request` trigger is unfiltered and the job always runs `.githooks/agent-checks` over the change's commits (the fleet default check, _agent-guidance ADR 0021) |
  | `propagation.yml` | `pull_request` (with `paths:`), `push` to main, schedule, dispatch | `pull_request` filtered on `on.pull_request.paths` (the workflow, `actions.lock`, `.claude/hooks/**`, `skills.lock`, `harness/**`, `scripts/eval_coverage.py`, `test/test_propagation.py`, `evals/propagation/**`, every `fixture.yaml` and `evals/non-coverage.yml`; `PropagationTriggerTests`); push, schedule and dispatch stay unfiltered because the arms probe an unpinned upstream registry (its header says why). `coverage` is informational and not required: absent optional registry access makes its census unresolved without testing a PR, so PR/push/dispatch record a warning while schedule fails. Only `coverage-publish` on schedule writes `persistent/eval-results`; the optional private checkout uses a token minted from the read-only registry GitHub App (variable `REGISTRY_READ_APP_CLIENT_ID`, secret `REGISTRY_READ_APP_PEM`) in that checkout step alone. |
  | `dependabot-auto-merge.yml` | `pull_request`, schedule, dispatch | acts only on Dependabot PRs whose changes stay inside the manifest-path allowlist |
  | `eval.yml` | dispatch only | no push or PR trigger; Adam's 2026-10-06 decision retired its Tuesday schedule because the [weekly routine](https://github.com/Adam-S-Daniel/skills-evals/pull/331) replaces it; its `plan` job refuses in-place fixtures (top-level `context:`) before any credential is minted and lists them in the step summary, since only the routine hosts in-place delivery ([#587](https://github.com/Adam-S-Daniel/skills-evals/issues/587)); a dispatch left with nothing to run ends successfully having minted nothing |
  | `roster-refresh.yml` | schedule, dispatch | no push or PR trigger, so no path filter; dispatches eval.yml with roster_only=true weekly so the roster follows current use |
  | `scheduled-run-health.yml` | schedule, dispatch | no push or PR trigger, so no path filter |
  | `routine-eval-fire.yml` | dispatch only | none needed; its `run-name` carries the mode and target (fixture, candidate, skill or section), which `scripts/improve_outcomes.py` and the allowance guard read; `guidance-improve` mode takes a `section` and runs `scripts/guidance_improve_gate.py fire-check` and `scripts/plan_week.py guidance-headroom` (refuses a section under 0.10 train headroom) before the bearer is in any env |
  | `routine-eval-weekly.yml` | schedule, `workflow_run` of the ingest and health-audit workflows, dispatch | no push or PR trigger; dispatch (no inputs) reruns the sweep when GitHub skips the schedule, as on 2026-10-27; it re-plans from the newest results after every ingest, with the daily health audit as a backstop and its last job arming `routine-eval-watchdog.yml`, so room left by overestimated fire costs is spent (Adam, 2026-10-31; a three-hourly cron never started), and the `routine-eval-weekly` concurrency group (not a required check) keeps two sweeps from overlapping; replaces `eval.yml`'s Tuesday schedule per Adam's 2026-10-06 decision; `scripts/plan_week.py` plans eval and improve fires by band within the allowance (ADR 0010 decision 4 addendum, 2026-10-26) and dispatches them one at a time through `routine-eval-fire.yml`, at most three in flight; while the routine is down (#583) it is probe-only, one paired eval fire at a time with improve and bare fires held, until a paired eval fire on a known cell delivers; the top eligible guidance section is one `guidance-improve` fire (`section`, `trials=3`); the plan job uploads the value-ranked improve candidates (skills and guidance sections) as the `improve-ranking` artifact; from 2026-11-09 17:00 UTC it plans within the two-week batch (`--batch-policy evals/batch-policy.yml`), and only when a plan starts a batch does the `batch-publish` job (`contents: write`, three push attempts) commit `batches/current.json` and `batches/<number>.json` to `persistent/eval-results`; its `work-issues` job (`issues: write`, `scripts/work_item_issues.py`) files one issue per `fixture-broken` cell and `routine-outage` the plan lists, and closes it once the plan stops listing it; a fire with no results past the routine's eval stop plus 10 minutes (`scripts/routine_deadlines.py`) frees its cell for a re-fire once the routine has delivered since |
  | `routine-eval-watchdog.yml` | dispatch (by every `routine-eval-weekly.yml` run's last job), schedule | no push or PR trigger, so no path filter; `scripts/plan_week.py watchdog` re-plans the sweep when a guard hold still running at the sweep's end expires (plus 2 minutes) or 50 minutes on, because a fire that never pushes results wakes no ingest; a dispatched run sleeps (wait mode) and stands down if a newer sweep starts, and a newer one cancels it (`cancel-in-progress`); the schedule is a no-sleep backstop that stands down while a timer is armed or a sweep is queued or running; not `workflow_run`, which GitHub stops at three levels (push, ingest, sweep) |
  | `routine-eval-results-pushed.yml` | `push` to `claude/eval-*`, except `!claude/eval-cost-*` | `paths: eval-results/**` (the routine's pinned result root); the exclusion keeps a cost branch off this trigger (#572); holds no permissions and runs nothing from the branch |
  | `routine-eval-cost-pushed.yml` | `push` to `claude/eval-cost-*` | `paths: improve-cost/**` (the one file an improve run's cost branch adds, #572 part 1; disjoint from `eval-results/**`, `eval-improve/**` and `eval-guidance-improve/**`); holds no permissions and runs nothing from the branch |
  | `routine-eval-ingest.yml` | `workflow_run` of the two above, dispatch | runs the default branch's copy only; `scripts/ingest_routine_results.py` dispatches on the branch regex (`kind` eval or cost): an eval branch is validated and written to `persistent/eval-results` `routine-results/<run id>/` (ADR 0010 decision 2), then its `estimate` subcommand adds that run's `cost_estimate.json`, calibrated on the runs already there; a cost branch must add exactly `improve-cost/<run id>/cost.json` passing `scripts/improve_cost.py`'s `check_record`, for a target that is not a private skill, and lands at `improve-costs/<run id>.json` (first record per run id wins; pyyaml installed for cost only); a rejection of either kind ends the run red; a cost ingest also wakes `explorer-data.yml` and the weekly top-up |
  | `routine-improve-pushed.yml` | `push` to `claude/eval-improve-*` | `paths: eval-improve/**` (the one directory an improve branch adds to; disjoint from `eval-results/**`, which is what keeps it off the results ingest); holds no permissions and runs nothing from the branch |
  | `routine-improve-gate.yml` | `workflow_run` of the above, dispatch | runs the default branch's copy only; `scripts/improve_gate.py` validates the branch without running it, builds the registry commits with no credential (`prepare`), then a PR in adam-agentskills is opened with a GitHub App token, minted only when secrets `EVAL_IMPROVE_APP_CLIENT_ID` and `EVAL_IMPROVE_APP_PEM` both exist; `evals/improve-policy.yml` `improve_merge_mode: auto` makes it ready with auto-merge (merge commit), `draft` (or a plugin that runs code) a draft (ADR 0005, routine improve mode and automatic merge addenda) |
  | `routine-guidance-improve-pushed.yml` | `push` to `claude/eval-guidance-improve-*` | `paths: eval-guidance-improve/**` (the one directory a guidance improve branch adds to; disjoint from `eval-results/**` and `eval-improve/**`, which keeps it off the results ingest and the skill gate); holds no permissions and runs nothing from the branch |
  | `routine-guidance-improve-gate.yml` | `workflow_run` of the above, dispatch | runs the default branch's copy only; `scripts/guidance_improve_gate.py` validates the branch without running it, builds the _agent-guidance commit with no credential (`prepare`, inside repo-settings ADR 0014's allowlist), then mints the eval-improve App token for `_agent-guidance` only under `continue-on-error` and opens the PR from `eval-guidance-improve/<section>`: ready with auto-merge (merge commit, `--match-head-commit`) in `improve_merge_mode: auto`, a draft otherwise; no token or a failed mint opens nothing and succeeds (ADR 0005, routine guidance improve mode addendum) |
  | `routine-scaffold-pushed.yml` | `push` to `claude/scaffold-*` | deliberately no path filter: every push must reach the gate, whose first job turns off auto-merge on the branch's open PR (an armed PR follows the branch); holds no permissions and runs nothing from the branch |
  | `routine-scaffold-gate.yml` | `workflow_run` of the above, dispatch | runs the default branch's copy only; `disarm` turns auto-merge off, `scripts/scaffold_real_work.py gate` validates the branch without running it (checker files must be the merge commit's own; checker sources are parsed as data with Python's `ast`, Ruby's Ripper and the Acorn of the trusted `evals/browser-testing/seed` lockfile, for #595's interface-string provenance), then the roster App opens the PR ready, labeled `eval-scaffold`, with auto-merge on (merge commit, `--match-head-commit`); no App token opens a draft and arms nothing (ADR 0003's 2026-10-26 addendum) |
  | `routine-draft-skill.yml` | daily schedule, dispatch | no push or PR trigger, so no path filter; picks one `new-skill` lesson from adam-agentskills-private's `lessons/` on `persistent/lessons` (read-only registry App token) or one owner-filed open `skill-proposal` issue in adam-agentskills with a "Skill name:" line (job token, `issue-proposals/` path), skipping drafted subjects and existing skills, re-admitting subjects whose hook proposal was closed as not planned, and dispatches draft mode through `routine-eval-fire.yml` when one fire fits the weekly allowance |
  | `routine-draft-skill-pushed.yml` | `push` to `claude/draft-skill-*` | `paths: draft-skill/**, evals/**` (the two directories a draft branch adds to; no other routine signal matches the branch); holds no permissions and runs nothing from the branch |
  | `routine-draft-skill-gate.yml` | `workflow_run` of the above, dispatch | runs the default branch's copy only; `scripts/draft_new_skill.py validate` judges the branch without running it; hook-first opens a `Hook proposal: <subject>` issue (job token, `issues: write`); accepted opens a skill PR in adam-agentskills (App token, as the improve gate) and then a fixtures PR here, opened with the roster App token (job token only as a warned fallback, because GitHub holds a `github-actions[bot]` PR's runs at `action_required`, #618); both drafts, or in `improve_merge_mode: auto` (`improve_gate.py merge-mode`) both ready, the skill's with auto-merge and the fixtures' armed later by `draft-fixtures-follow.yml` once the skill has merged |
  | `draft-fixtures-follow.yml` | `workflow_run` of `routine-eval-ingest.yml` (completed), dispatch (no schedule: it handles `eval-improve/` branches) | no push or PR trigger, so no path filter; default branch only, no concurrency group; for each open non-draft `draft-skill-fixtures/<subject>` PR whose `draft-skill/<subject>` PR in adam-agentskills has merged, the roster App token brings a `github-actions[bot]`-opened PR up to date (`update-branch`, which restarts its held checks) and turns on auto-merge (merge commit); a skill closed unmerged is left for a person; never approves, closes, force-pushes or deletes |
  | `loop-pr-refresh.yml` | `workflow_run` of `routine-eval-ingest.yml` (completed), dispatch (no schedule: it handles `eval-improve/` branches) | no push or PR trigger, so no path filter; default branch only, no concurrency group (#623); for each open loop PR whose head conflicts with its base (adam-agentskills `draft-skill/`, `eval-improve/`, `retire-skill/`; here `draft-skill-fixtures/`), `scripts/refresh_loop_prs.py merge` merges the base in a fresh clone and re-resolves only the append-only paths (`docs/skill-impact.md`, `scripts/plugin_layout.json`, `README.md`'s layout, `evals/unscheduled.yml`), then pushes the merge commit (never a force-push) with the eval-improve App token (adam-agentskills) or the roster App token (here), each minted under `continue-on-error`, so the PR's checks run again; any other conflict is left for a person and named in the job summary |
  | `skills-lock-bump-dispatch.yml` | `workflow_run` of `routine-eval-ingest.yml` (completed), dispatch | no push or PR trigger, so no path filter; default branch only, no concurrency group, no schedule (this repository's cron is unreliable; _agent-guidance's own cron is the backstop); `scripts/skills_lock_bump_due.sh` decides from _agent-guidance's `skills-lock-bump.yml` runs and adam-agentskills' main commit time (job token, both public) whether a run is due: main changed after the second-newest run started, none queued or running, none started in the last 30 minutes; then the eval-improve App token, minted for `_agent-guidance` alone with Contents write under `continue-on-error`, sends `repository_dispatch` `skills-lock-bump` there (_agent-guidance#413) |
  | `routine-fixture-supply.yml` | daily schedule, dispatch | no push or PR trigger, so no path filter; mines merged fleet PRs, `scaffold_real_work.py pick` fires up to 3 new candidates in scaffold mode through `routine-eval-fire.yml` (within the allowance guard), and `scaffold_real_work.py promote` opens an auto-merging PR (roster App) that moves drafts with 2 clean ingested runs onto `evals/scheduled.yml` |
  | `explorer-data.yml` | `workflow_run` of `routine-eval-ingest.yml` (completed), daily schedule, dispatch | no push or PR trigger, so no path filter; `build` (read-only, `issues: read`, and `actions: read` for one `continue-on-error` step that lists the last 14 days of `routine-eval-fire.yml` runs into `--fire-runs`, prints only `fire runs unavailable (exit N)` on failure and holds `GH_TOKEN` in that step alone) runs `scripts/explorer_data.py` on main's copy, the results branch, the public registries, `_agent-guidance` and the in-place fixtures' consumer repos (repo-settings and wsl-automation checked out too), all with full history (`fetch-depth: 0`; adamdaniel.ai also `filter: blob:none`) and passed as `--context-repo`, for a report-only alert over public, non-private, scheduled in-place skill fixtures only: `context-drift` (#545: the skills beside it moved on the consumer's first-parent history at least 7 days ago; `drift_since`), plus a `context_drift_unknown` count, and a report-only `loaded-copy` alert per public skill and surface (#562: the leading copy sessions loaded in the last 2 weeks of `skill-digest` rows, by invocations with every tied copy, is none of the digests main had in that window, read from the registry checkouts' full history; it lags a main change by up to the window, and each skill's `copies` field carries the per-copy counts); a shallow checkout makes them unknown, never clean. The document-level `fires_without_results` (#555) counts successful paired eval fires on in-scope (public, non-private, scheduled) fixtures that brought back no results or none that validated, with their 60-minute sweeps; null (unknown) without a readable fire file. `publish` (the only `contents: write`) commits `explorer/latest.json` to `persistent/eval-results` when it changed apart from `generated_at` and `source.results_commit`; a skill appears only if the coverage census lists it in a registry with `private: false` (#72) |
  | `skill-coverage.yml` | daily schedule, dispatch | no push or PR trigger; reads all four registries for a redacted census, publishes on schedule or explicit non-dry dispatch, and proposes up to three public GAP drafts; its `retirement` job runs on schedule only, computes the #70 verdicts from `persistent/eval-results` and acts on a `retire` one: in `retirement_mode: auto` (committed) a ready, `agent-authored`, auto-merging removal PR in adam-agentskills, written with the improve gate's GitHub App token (`EVAL_IMPROVE_APP_CLIENT_ID`/`EVAL_IMPROVE_APP_PEM`, minted under `continue-on-error` in the step before the one that uses it, passed as `REGISTRY_TOKEN`), with full registry history (`fetch-depth: 0`); with no token, or for a plugin that runs code, it files or updates a retirement issue instead (`issues: write`, `--fallback-to-proposal`); it opens nothing while an `eval-improve/`, `draft-skill/` or `retire-skill/` PR is open there; then does the same for one guidance section (`--target guidance`, #124), opening the removal PR in `_agent-guidance` with an eval-improve App token minted for that repo alone, or filing the issue when that token is absent; its `regression` job (daily and on dispatch, where it is a dry run unless `dry_run` is false; `issues: write`) runs `scripts/regression_issue.py` over `harness/regression.py` and files, updates or closes one `Regression:` issue per skill or guidance section in skills-evals, thresholds in `evals/regression-policy.yml` (#69, #121); on schedule its `regression-publish` job commits the document to `persistent/eval-results` at `regressions/latest.json` (`contents: write`, no concurrency group, three push attempts) |
  | `site-sync.yml` | `push` to main with `paths: [tool/index.html]`, dispatch | filtered by `on.push.paths` (not a required check); vendors the explorer page into adamdaniel.ai as a `tool-sync/skills-evals` PR with auto-merge (`--squash`, the site is cms-platform-managed), authenticated by the eval-improve App token minted for `adamdaniel.ai` alone under `continue-on-error`; without the secrets or the App install it warns, writes the fix to the step summary and succeeds (`scripts/sync_to_site.sh`, `test/issues/test_issue_72_site_sync.py`) |
  | `site-preview.yml` | `pull_request` (opened, synchronize, reopened, closed) | deliberately unfiltered at the trigger: the teardown leg must run even when the final diff does not touch the page, so step `relevance` checks for `tool/index.html`; mirrors a changed page to a draft `tool-preview/skills-evals-pr-<n>` PR in the site repo and comments the `/tools/evals/` preview URL (`scripts/upsert_comment.sh`); not a required check, so it keeps its concurrency group; same soft-skip without the App token |

### Action pins

Workflows name third-party actions by release tag; [`.github/workflows/actions.lock`](.github/workflows/actions.lock) locks each tag to an exact commit, and the runner runs the locked commit even when it disagrees with the tag. The `test` job's "Verify action lockfile" step is the shared action [`Adam-S-Daniel/verify-actions-lock`](https://github.com/Adam-S-Daniel/verify-actions-lock); it runs `gh actions-lock --verify` only when a PR touches workflow dependencies (`.github/workflows/**`, `.github/actions/**`, an `action.yml`/`action.yaml`) and fails on any finding except `cooldown-config-ignored` (dependabot.yml's cooldown `exclude`, which the tool ignores). It is early feedback, not the only guard: the runner rejects forged pins, and GitHub's Require lockfile policy is on. Write the exact tag by hand, regenerate with `gh actions-lock --no-narrow`, and commit both files; review an `actions.lock` diff as you would a SHA pin. A stale or moved pin is fixed with `gh actions-lock --accept-moved`; review the diff. A `reachability-unknown` failure means the GitHub API was unreachable: re-run. Cross-repo reusable workflows (`jobs.<id>.uses`) are not locked, so they take a full commit SHA (`Adam-S-Daniel/cms-platform` refs excepted); a test enforces it. Fleet rule: [ADR 0024](https://github.com/Adam-S-Daniel/_agent-guidance/blob/main/docs/decisions/0024-actions-pin-through-lockfiles.md).
