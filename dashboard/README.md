# Project dashboard

A status page for the self-improvement loop: test results and the weekly
allowance, real-work usage, the loop's stages, cleanup, routines, threads, and
what waits on you. It is a claude.ai Dashboard artifact: the page
(`page/index.html`) plus named datasets (`page/datasets.json`). Some datasets
load live through the GitHub connector. The rest are JSON snapshots that
`build.py` writes and a refresh session uploads.

## Layout

| Path | What it is |
|---|---|
| `build.py` | Builds every snapshot dataset from the results branch, `evals/budget.yml`, `evals/roster.yml`, the input dumps and the config |
| `page/index.html` | The page: layout, calcs and tables |
| `page/datasets.json` | Every dataset's title, description and source. Live ones are GitHub connector queries; snapshot ones are `file` sources that point at an uploaded blob |
| `config.example/` | The owner's own lists, in invented data. Keep the real copy outside this public repo |
| `inputs.example/` | The read dumps a refresh collects, in invented data |
| `smoke/` | Renders the page with a mocked runtime and fails on any page error |
| `tasks/` | Prompts for the scheduled tasks that keep the page current |

## Refresh

A refresh session runs these steps. `tasks/refresh.md` is the scheduled-task
prompt that tells it to.

1. **Results branch.** In a skills-evals checkout at `origin/main`, run
   `git fetch origin persistent/eval-results`, then extract the branch into an empty
   directory: `git archive origin/persistent/eval-results | tar -x -C <results>`.
2. **Inputs.** Write each dump into `<inputs>/` (shapes in `inputs.example/`):

   | File | Source |
   |---|---|
   | `threads.json` | `list_threads` (all pages), its `sessions` entries: `thread_id`, `title`, `state`, `last_activity_at`, `resolved` |
   | `triggers.json` | `get_trigger` for each routine in `config/routines.json` with `source.kind: trigger`, keyed by id: `enabled`, `next_run_at`, `last_run.{status,fired_at}` |
   | `trigger_list.json` | `list_triggers` with `recurring: false`, `enabled: true` (all pages): `id`, `name`, `run_once_at`, `enabled`, `hearth_channel_id` |
   | `workflow_runs.json` | `actions_list` `list_workflow_runs` for each `source.kind: workflow` routine, keyed `owner/repo:workflow.yml`: `created_at`, `status`, `conclusion`, `html_url` |
   | `workflow_states.json` | `actions_get` `get_workflow` for the same workflows, keyed the same way: its `state` (`active`, `disabled_manually`, ...). A workflow that is not `active` shows as Paused; a missing file reads as active |
   | `needs_owner.json` | `search_issues` with `label:needs-owner is:open user:<owner>`, for each owner in `site.json` `github_owners`: `title`, `html_url`, `repository_url`, `state`, `created_at`, `labels` |
   | `waiting_reviews.json` | `actions_list` `list_workflow_runs` with `status: waiting` in each `environment_review_repos` repo: `repo`, `name` (the display title), `environment`, `head_sha`, `created_at`, and `job_url`, the waiting job's page (`list_workflow_jobs`) |
   | `open_pr_heads.json` | Open PRs' head shas, keyed by repo, for the same repos (`list_pull_requests`, `state: open`) |
   | `link_states.json` | Optional. `{url: "open" \| "closed" \| "merged"}` for each `waiting_manual` link |
   | `loop_status.json` | The loop's gap list (`gaps[]`: `gap`, `title`, `status`, `owner`, `pr`), kept by the loop thread |
   | `session_costs.jsonl` | One line appended per thread session on every refresh, from `get_session` on every thread session active since the last refresh: `v`, `at` (when sampled), `source` (`backfill` or `refresh`), `thread_id`, `session_id`, `created_at`, `updated_at`, `cost_usd` (the session's cumulative API-equivalent dollars, `ccr.external_metadata.usage.cost_usd`), `output_tokens`, `error` (`null` or `not_found`) |
   | `owner_messages.jsonl` | One line per message the owner wrote in the project, from `read_project_chat` and `read_thread` on threads active since the last refresh: `v`, `message_id`, `sent_at`, `thread_id`. The owner's own messages only, ids and times only, never text |
   | `loop_prs.json` | Pull requests from GitHub search by head-branch prefix (`eval-improve/`, `draft-skill/`, `retire-skill/`, `eval-guidance-improve/`, `retire-guidance/`) in adam-agentskills and _agent-guidance: `repo`, `number`, `url`, `head_ref`, `title`, `state`, `merged_at` |

   `session_costs.jsonl` and `owner_messages.jsonl` are ledgers, not dumps: copy the
   previous run's file into the new inputs directory first, then append, so history
   is never lost.

   A missing optional dump builds as empty. Never paste a credential into a dump.
3. **Build.** `python3 dashboard/build.py --results <results> --inputs <inputs> --config <config> --out <ds>`.
   It needs PyYAML and imports `scripts/allowance_guard.py` and `scripts/eval_facts.py`,
   whose `scored_runs` builds `eval_runs` and `bare_runs`. The public explorer document
   (`explorer/latest.json`) carries the same rows and the page's summaries of them
   for public subjects only, so both read one copy of the logic. It refuses to write
   an empty dataset: an empty list reads as "failed to load" on the page, so
   empty lists get one placeholder row (key field `none`), which the page hides.
4. **Compare.** Upload only datasets that changed. Skip `eval_allowance` when
   only its timestamps and pace moved.
5. **Publish.** For each changed file, run Artifact `publish` with the dashboard's
   `url`, `asset: true` and `file_path`, one file per call. Then run one
   ArtifactData `batch` of `update` writes on `datasets/<id>`, pinned with
   `if_version`, that sets `source: {kind: "file", url: "/_blob/<id>", name}` and
   `updated: {at, by}`.
6. **Page changes.** Smoke-test first. Put d3@7.9.0's `dist/d3.js` in a work dir
   (`npm pack d3@7.9.0`), then run
   `python3 dashboard/smoke/mk.py dashboard/page/index.html <ds> <work> && node dashboard/smoke/run.js <work>`.
   It exits non-zero on any page error. Then write the page to ArtifactData
   `files/index.html` (field `text`) with `if_version`.
7. **Check the merge relays.** For each "Dashboard refresh: <repo> merges" task,
   compare its `last_run` with the PRs merged since the previous refresh. A merge
   with no run means the GitHub trigger did not fire: fix it, or tell the owner.

The run console is fed by the watcher: it writes `inputs/run_stream.json` (workflow
runs from `gh api repos/<repo>/actions/runs?created=>=<7 days ago>`, plus
scheduled-task runs from `list_triggers`/`get_trigger`, accumulated across passes)
and uploads `run_stream.json`.

## Red in CI runs

`ci_red_runs` lists every agent-checks CI run that failed, newest first, from the
`red_runs` list in `usage/weekly-ci.json` (written by _agent-guidance's daily
impact report). A public repo's run links its run page; a private repo's run keeps
only its week. The Real-work impact tab shows it under "By week", and both "By
repo" and "By week" carry a "Red in CI" column.

## Cost and benefit

`build.py` writes two datasets for the Cost and benefit tab. A week runs Monday
17:00 UTC to the next Monday and is labeled by its start date; the first is set by
`COST_START`.

- `cost_benefit_weeks`: per week, plan eval runs (`run_count`, `run_meter_points` from the
  account meter, `run_points_est` from their dollars), API-billed eval dollars (`api_usd`,
  from `results/` summaries whose `usage.reasons.meter` is the harness's "API-billed run"
  text), project-thread spend (`build_usd`, `build_points`, `build_estimated`), loop
  changes merged, real-work reach, owner messages and decisions. `verdicts` is the current
  count of decided skill and guidance verdicts, on the latest week only.
- `cost_benefit_summary`: cost per verdict, decision yield, real-work reach, the Dec 15 bar
  (`bar_changes`, `bar_build`, and `bar_verdict` from Dec 16) and the points-per-dollar rate.

`build.py` also writes two datasets for the Fixture requests panel on the Self-improvement loop tab, from `fixture_queue` in `results/explorer/latest.json` (all issue and PR numbers are in skills-evals):

- `fixture_requests`: one row per request (key is the issue number): kind in plain words, state, age in days (open requests only), PR count and latest PR link, and the count, real-work count, runs and cost of the fixtures whose `request` names it. Open first, then oldest.
- `fixture_queue_summary`: one row of the queue's totals, finding counts and a `status` of `not-reported` (no `fixture_queue` in the file, or null), `attention` (any finding) or `ok`.

Project-thread spend is attributed from `session_costs.jsonl`: the rise in a session's
cumulative cost between two samples is spread evenly over the time between them, and cost
before its first sample is spread from the session's creation, which marks the week
estimated. It counts every thread in the project, not only the eval system's own work.
It misses scheduled-task sessions (routines and watch passes), which `get_session` on
threads does not see. Points per dollar is the account meter's reading divided by all
API-equivalent spend over complete weeks, so it is an upper bound; with no such week it
falls back to `DEFAULT_POINTS_PER_USD`.

## What stays hand-maintained, and why

Everything else comes from a read. These lists are in `config/` because no
source holds them:

| Config | Why no read can supply it |
|---|---|
| `snapshots.json` `cleanup` | A fixed list agreed once, with a "done when" test per item. Each status is checked against the linked PR or issue on refresh, but the list itself is a decision |
| `snapshots.json` `gate` | Conditions the owner set. Their status is a judgment over several runs and PRs |
| `snapshots.json` `decisions` | The owner's decisions, in words. They live in chat and memory, not in one queryable place |
| `snapshots.json` `waiting_manual` | Asks that exist only in a conversation. Each drops automatically once its link reads closed or merged in `link_states.json` |
| `routines.json` | Each routine's plain-English `what`, `schedule` and `note`. Last run, next run, result and health are read |
| `roster.json` | Plain-English `why` per model and the models just dropped. The list itself is read from `evals/roster.yml` |
| `loop.json` | The loop's stages, the per-subject grid and the lane notes. Stage status is derived from `loop_status.json` |
| `site.json` | Owner names, the project's thread link prefix, its channel id, and title overrides |

## What waits on you

`waiting` collects, in order:

1. Open issues and PRs labeled `needs-owner` in every owner's repos (the fleet
   worker adds the label), skipping any labeled `on-hold`.
2. Runs waiting on a required environment review, only on the current head of
   an open PR. Older runs on the same branch stay `waiting` forever and decide
   nothing.
3. Threads in the `blocked` state.
4. Cleanup items marked `waiting_on_you`, grouped by reason.
5. `waiting_manual` items whose link is not closed or merged.

## Adopting it

1. Copy `config.example/` somewhere private and fill it in.
2. Create a Dashboard artifact. Write `page/index.html` to `files/index.html`,
   and each entry of `page/datasets.json` to `datasets/<id>`, with your owner and
   repo names in the live queries.
3. Run one refresh by hand, then schedule `tasks/refresh.md` every 2 hours.
   Add `tasks/merge-relay.md` as a GitHub-triggered task on each repo whose
   merges should refresh the page.
4. The page's notes (dated cap changes, the cleanup due date) are the owner's.
   Edit them in `page/index.html`.
