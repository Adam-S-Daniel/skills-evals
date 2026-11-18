# Project dashboard

A status page for the self-improvement loop: test results and the weekly
allowance, real-work usage, routines, threads, and
what waits on you. It is a claude.ai Dashboard artifact: the page
(`page/index.html`) plus named datasets (`page/datasets.json`). Some datasets
load live through the GitHub connector. The rest are JSON snapshots that
`build.py` writes and a refresh session uploads.

## One app, three builds

The page is the private build of the Improvement Loop Explorer: `explorer/src` builds
`tool/index.html` (the public page, read from `latest.json`),
`page/index.html` (this page, read from the `explorer` dataset) and
`explorer/dist/artifact/index.html` (the public page as a claude.ai artifact,
below). Never edit `page/index.html` by hand: change `explorer/src`, run
`npm run build` in `explorer/`, and commit every page; `explorer/test/run.js`
and `npm run check` fail when any is stale.

`explorer/dist/artifact/index.html` is the public page for publishing as a
claude.ai artifact with `latest.json` as a file beside it. An artifact's
content security policy is `connect-src 'self' blob:`, so it cannot fetch
`latest.json` from raw.githubusercontent.com; this build reads the relative URL
`latest.json` from its own origin and takes no `?data=` override. It is the
public entry with `src/adapters/artifact.js` in place of `src/adapters/web.js`
(`explorer/build.js` swaps the import), so it shows the same public views and
holds no private code; `explorer/test/run.js` checks that it names no
raw.githubusercontent.com URL, fetches no literal URL and leaks nothing private.

| Group | Route | Private only |
|---|---|---|
| Summary | `#/summary` | Its waiting, routine and allowance tiles |
| Needs you | `#/needs` | Yes, and the page opens on it. Waiting on you (or "Nothing is waiting on you"), a loop health strip, one "Needs attention" list (a kind with more than 3 rows folds into one row whose title links to the whole set; every row links to its evidence, an alert with no URL to its subject's page), this week's allowance, routine health (problems first, healthy ones folded), the half-built banner only above 0 |
| Changes | `#/changes`, `#/changes/removed` | What the loop changed in 30 days with the reason, trending toward removal, where lessons went, fixture requests, lesson proposals; the live merged pull requests join the list |
| Results | `#/hooks`, `#/hooks/<check>`, `#/skills`, `#/skills/<name>`, `#/guidance`, `#/guidance/<id>`, `#/method` | Use by repo on a skill's page, the roster's "why" |
| Spend and use | `#/spend` | One spend panel, use across private repos, cost and benefit |
| Activity log | `#/activity` | Routines, check-ins, the run console, live PRs and issues, ingests, threads |

Routes are the same in both builds; `?subject=guidance`, the old tab hashes
(`#overview`, `#evals`, `#costbenefit`, ...) and the old routes (`#/loop`, `#/impact`,
`#/ops`, `#/removed`) redirect. A snapshot older than 25 hours shows a banner on every group. The public build has no
Needs you group, says "the owner" where this page says "you", and folds checks
in private repos into one row. Its bundle never holds private view code,
private dataset ids or `dash` (an AST check in `explorer/test/run.js`).

Each private panel reads its datasets through `explorer/src/private/` and
hides when they are empty, loading or only a placeholder row. Where a private
dataset covers a public panel (use, cost, runs, PRs and
issues), the private one replaces it. The optional `explorer_private` dataset
(private-skill results, same schema) merges in with a "Private" badge.

## Layout

| Path | What it is |
|---|---|
| `build.py` | Builds every snapshot dataset from the results branch, `evals/budget.yml`, `evals/roster.yml`, the input dumps and the config |
| `page/index.html` | The page, generated from `explorer/src` (see above) |
| `page/datasets.json` | Every dataset's title, description and source. Live ones are GitHub connector queries; snapshot ones are `file` sources that point at an uploaded blob |
| `config.example/` | The owner's own lists, in invented data. Keep the real copy outside this public repo |
| `inputs.example/` | The read dumps a refresh collects, in invented data |
| `smoke/` | Renders the page with a mocked runtime and fails on any page error |
| `refresh/` | The refresh helpers (see Refresh); every one reads and writes only under `DASHBOARD_HOME` |
| `tasks/` | The prompt for the scheduled task that keeps the page current |

## Refresh

The refresh is a procedure in this file plus the helpers in `refresh/`; the
owner's data stays outside this public repo, in one private folder named by
`DASHBOARD_HOME` (`config/`, `inputs/`, `ds/` and `watch/`). Every helper stops
when `DASHBOARD_HOME` is unset. `tasks/refresh.md` is the scheduled-task prompt:
it names only this file, the private folder and the dashboard's URL, so a change
to the procedure is a pull request here, never an edit to the task.

### Every run, in order

**Who runs what.** The main session only dispatches, as `tasks/refresh.md` "Run" says: it
runs on Opus whatever the task page says, and each of its calls re-reads a context that starts
near 100k tokens. Steps 1 and 3, step 2, and step 5 (with its fire cost ledger) run in three
Haiku subagents at once; their tool output is large (every thread, the owner's new messages,
every session and every scheduled task). Each writes its result straight to the file or helper
the step names (step 5 also writes arg 1 to `$REFRESH_WORK/arg1.json` and the run list for
step 6 to `$REFRESH_WORK/runs.json`) and returns one line: its counts, or the `STOP:` text.
Steps 0, 4 and 6 to 12 run after them in one Sonnet subagent, which reads those files
(`"$(cat "$REFRESH_WORK/arg1.json")"` as arg 1) and handles every `STOP:` itself. Why: on
2026-11-15 a run that made the listing calls itself grew to 324k tokens and cost $5.43, and on
2026-11-18 a run that kept steps 0, 4 and 6 to 12 in the Opus session made 47 Opus calls.

0. **Setup.** In a skills-evals checkout run `git fetch origin main && git checkout --detach origin/main`
   before anything else (helpers are read from that commit; `refresh.sh` never checks out),
   and `export DASHBOARD_HOME=<private folder>`; run every later step from the checkout's root.
   The session needs these repos attached (add_repo, push access for the gh API): skills-evals,
   adam-agentskills-private when `page/datasets.json` defines `explorer_private` (cloned beside
   skills-evals, or at `AGENTSKILLS_PRIVATE`), and every repo named in `site.json`
   `run_console_repos`, `loop_pr_repos`, `environment_review_repos` and `extra_workflows`.
1. **Threads.** Rebuild `inputs/threads.json` from the FULL `list_threads` listing, every page,
   never a patch: `thread_id`, `title`, `state`, `last_activity_at`, `resolved`, `session_id`.
   For each new thread, `get_session` it and add its branch suffix to `inputs/thread_branches.json`.
2. **Owner messages (ledger).** Read `inputs/owner_messages_read.json` `read_through` and
   `chat_cursor`. Note the current time, then:
   - `read_project_chat` pages oldest first. Start from `cursor: <chat_cursor>` when it is set
     (a refused cursor means start with none) and follow `cursor` until `has_more` is false.
     Keep the cursor that fetched the LAST page (the saved one when only one page came back).
     Without it, every run paged the whole chat, 20 pages and about 370k characters on
     2026-11-18, to find six new messages.
   - `read_thread` every thread active since `read_through` (`list_threads since`), with
     `order: "newest_first"`, `limit: 20`, stopping once a page reaches messages older than
     `read_through`.

   Pass the owner's own messages, ids and times only, to
   `python3 -I dashboard/refresh/append_owner_messages.py --read-through <the time you noted> --chat-cursor <the cursor you kept> '<json>'`
   (or `@file`). It skips ids already present and keeps the saved cursor when `--chat-cursor` is left out.
3. **Session costs (ledger).** For every thread session active since the last refresh,
   `get_session` (its id with the `session_` prefix: `list_threads` gives `cse_`, and the
   2026-11-18 run lost 19 of 26 calls to errors) and append with `python3 -I dashboard/refresh/append_session_costs.py '<json list>'`
   (fields in that script; `cost_usd` is `external_metadata.usage.cost_usd`, a 404 is error `not_found`).
4. **Loop PRs.** `bash dashboard/refresh/loop_prs.sh`.
5. **Scheduled tasks.** `list_triggers` (every page; it pages early by size) plus `get_trigger`
   for every on-demand task in `config/routines.json` (empty `source.cron`). Build arg 1:
   `{id: {enabled, cron_expression, next_run_at, last_run, created_at}}` for every non-retired
   trigger row. `refresh.sh` fills a row's missing `added` date from `created_at`. Also refresh
   `inputs/trigger_list.json` (one-shot tasks; drop ones that have run).
   - **Fire cost ledger.** The ledger is `spend/routine-fires.jsonl` on the private
     `persistent/usage-events` branch of `Adam-S-Daniel/adam-agentskills-private` (attach it
     with `add_repo`, push access): it names private tasks and session ids, so it never goes in
     this public repository. Shallow-clone that branch (`git clone --depth 1 --branch
     persistent/usage-events ...`) and export `ROUTINE_FIRES_LEDGER=<clone>/spend/routine-fires.jsonl`.
     Also sparse-clone `.github/workflows` of `Adam-S-Daniel/_agent-guidance` to
     `<root>/_agent-guidance/.github/workflows` (`git clone --depth 1 --filter=blob:none --sparse`,
     then `git sparse-checkout set .github/workflows`) and export `WORKFLOWS_ROOT=<root>`: the fleet
     worker's runs a week come from the workflow that fires it. `refresh.sh` stops when either is
     missing, since scheduled-task cost would read as no value.
     For each of the rows above whose `last_run.session_id` is not yet in the ledger and whose
     `last_run.finished_at` is set, read the session's final
     cost: `list_events` with `kinds: ["result"]`, `limit: 100`, no cursor, and take
     `total_cost_usd` from the newest result; also `get_session` (`session_` prefix) for
     `external_metadata.usage.cost_usd` and `last_served_model`. Append with
     `python3 -I dashboard/refresh/append_routine_fires.py '<json list of {trigger_id, name, fired_at, finished_at, status, session_id, total_cost_usd, session_usage_cost_usd, last_served_model}>'`;
     it skips session ids already present. When it appended any, commit only that file
     (noreply identity, message `spend: routine fires`) and push with
     `bash scripts/push_with_rebase_retry.sh origin persistent/usage-events` from the clone.
     Only `last_run` is visible, so a task that fires more than once between refreshes loses
     the fires in between. acsi-kit's plan model and `scripts/automatic_spend.py` read this ledger.
6. **Run console.** `python3 -I dashboard/refresh/collect_runs.py '<list of {trigger_id,name,fired_at,finished_at,status}>'`.
   It keeps 7 days of workflow runs from `site.json` `run_console_repos` and of scheduled-task
   runs in `inputs/run_stream.json`.
7. **Build.** `bash dashboard/refresh/refresh.sh '<arg 1>' '{}'`, with `ROUTINE_FIRES_LEDGER` and
   `WORKFLOWS_ROOT` exported from step 5 (it stops without them). It runs `half_built.sh`, reads
   workflow runs and states, builds every dataset into `$REFRESH_WORK/ds_now` (default
   `/tmp/dashboard-refresh/ds_now`) and lists what changed.
   - A line starting `STOP:` means an input is missing or stale. Do what it says and run it
     again. Never edit a dataset or input by hand to get past it.
   - A line starting `MISSED:` means an earlier scheduled run never happened. Put that in this
     run's log line.

   Build details: `build.py` needs PyYAML and imports `scripts/allowance_guard.py` and
   `scripts/eval_facts.py`. When `page/datasets.json` defines `explorer_private`, `refresh.sh`
   copies `explorer/private.json` from adam-agentskills-private's `persistent/eval-results`
   branch on every run and stops if it cannot be read, since an unstamped copy ages the header.
   `build.py` copies `explorer/latest.json` unchanged into the `explorer` dataset and refuses to
   build without it. It refuses to write an empty dataset: an empty list reads as "failed to
   load" on the page, so empty lists get one placeholder row (key field `none`), which the page hides.
8. **Compare and publish.** Upload only datasets that changed. Still set `updated` on every `file` dataset the build wrote, changed or not, `budget`, `roster` and `explorer_private` included (each is read fresh every run). The dashboard header's "Updated <age>" is the OLDEST `updated.at` of all file datasets, so one dataset left unstamped makes the whole page read days old (2026-11-13: `budget`, last stamped Nov 9, made it say "Updated 4 days ago" after a run that morning). Every dataset goes stale after 50 hours (two refresh intervals plus two). Skip `eval_allowance` when
   only its timestamps and pace moved. Never skip `refresh`: it changes every run, and the page's
   "refresh did not land" banner reads it.
   For each changed file, run Artifact `publish` with the dashboard's `url`, `asset: true` and
   `file_path`, one file per call. Then run one ArtifactData `batch` of `update` writes on
   `datasets/<id>`, pinned with `if_version`, that sets
   `source: {kind: "file", url: "/_blob/<id>", name}` and `updated: {at, by}`. Delete any
   `datasets/<id>` doc that `page/datasets.json` no longer names.
   On `PAGE-CHANGED`, build the page in `explorer/` (`npm ci && npm run build`), smoke-test it with
   `python3 dashboard/smoke/mk.py dashboard/page/index.html <ds> <work> && node dashboard/smoke/run.js <work>`
   (`<work>` is any empty directory; it exits non-zero on any page error), then write it to
   ArtifactData `files/index.html` (field `text`) with `if_version`; keep the `dash/look` doc.
   Then `bash dashboard/refresh/mark_published.sh` (add `page` if you wrote the page): it copies
   what is now live into `$DASHBOARD_HOME/ds`, the baseline the next run compares against.
9. **Spend.** Keep `ROUTINE_FIRES_LEDGER` and `WORKFLOWS_ROOT` exported from step 5, and build
   with `--spend` (below) plus `--workflows-root "$WORKFLOWS_ROOT"`: the spend file's
   `loop_jobs` (the loop's automatic jobs' weekly meter use) needs both, and
   `scripts/allowance_guard.py` refuses every fire once it is missing or 3 days old. When the
   weeks or `loop_jobs` changed, push only
   `spend/weekly.json` from a detached worktree at origin/main to
   `claude/spend-<YYYYMMDDTHHMMSSZ>` (noreply identity); check the "Ingest routine eval results"
   run is green.
10. **Routine rows.** Reread each row's `schedule` and `note` in `config/routines.json` against
    what step 5 and `inputs/workflow_runs.json` show, and rewrite any sentence that is no longer
    true. A task fired by a workflow on a cadence variable (a repository variable the fire job
    prints): runs whose log says "skipped" did not fire it, and `expect_every_hours` must equal
    that cadence.
11. **Log.** Append one line to `$DASHBOARD_HOME/watch/log.md`:
    `- <UTC start> <UTC end> refresh: <counts, what changed>`.
12. **No backstop wake.** Do not `send_later` to this session. The task starts a fresh thread
    each run, and a wake into a finished run's thread reloads its whole context (300k tokens or
    more) just to read one log line. A run that never happens is caught by the next one, whose
    build prints `MISSED:` (step 7); that run says so in its log line and in its thread.

### Standing rules

- Fix the automation, not the data. A wrong number on the page means a step or check is
  missing; add it here or in `refresh/`, then rerun.
- Reply in the owner thread only when something needs the owner; otherwise update the checklist.
- Other sessions do not edit `DASHBOARD_HOME`; they send changes to the session that owns the
  refresh, or open a pull request here.
- Page wording: "git hook" or "Claude Code hook", never bare "hook"; "you", never the owner's
  name. Times show in US Eastern.
- Config edits go in `$DASHBOARD_HOME/config/`, never in build code. `explorer_private.json`
  goes only to the private artifact, never to `ds/` or anything public.

### Inputs

Each dump lives in `$DASHBOARD_HOME/inputs/` (shapes in `inputs.example/`):

| File | Source |
|---|---|
| `threads.json` | `list_threads` (all pages), its `sessions` entries: `thread_id`, `title`, `state`, `last_activity_at`, `resolved` |
| `triggers.json` | Written by `refresh/refresh.sh` from its first argument (step 5) |
| `trigger_list.json` | `list_triggers` with `recurring: false`, `enabled: true` (all pages): `id`, `name`, `run_once_at`, `enabled`, `hearth_channel_id` |
| `workflow_runs.json` | Written by `refresh/refresh.sh`: the latest runs of every `source.kind: workflow` routine plus `site.json` `extra_workflows`, keyed `owner/repo:workflow.yml` |
| `workflow_states.json` | Written by `refresh/refresh.sh` for the same workflows: each one's `state`. A workflow that is not `active` shows as Paused; a missing file reads as active |
| `needs_owner.json` | `search_issues` with `label:needs-owner is:open user:<owner>`, for each owner in `site.json` `github_owners`: `title`, `html_url`, `repository_url`, `state`, `created_at`, `labels` |
| `waiting_reviews.json` | `actions_list` `list_workflow_runs` with `status: waiting` in each `environment_review_repos` repo: `repo`, `name` (the display title), `environment`, `head_sha`, `created_at`, and `job_url`, the waiting job's page (`list_workflow_jobs`) |
| `open_pr_heads.json` | Written by `refresh/refresh.sh`: open PRs' head shas in each `environment_review_repos` repo |
| `link_states.json` | Optional. `{url: "open" \| "closed" \| "merged"}` for each `waiting_manual` link |
| `session_costs.jsonl` | One line appended per thread session on every refresh, from `get_session` on every thread session active since the last refresh: `v`, `at` (when sampled), `source` (`backfill` or `refresh`), `thread_id`, `session_id`, `created_at`, `updated_at`, `cost_usd` (the session's cumulative API-equivalent dollars, `ccr.external_metadata.usage.cost_usd`), `output_tokens`, `error` (`null` or `not_found`) |
| `owner_messages.jsonl` | One line per message the owner wrote in the project, from `read_project_chat` and `read_thread` on threads active since the last refresh: `v`, `message_id`, `sent_at`, `thread_id`. The owner's own messages only, ids and times only, never text |
| `loop_prs.json` | Written by `refresh/loop_prs.sh`: pull requests in `site.json` `loop_pr_repos` whose head branch starts with a loop prefix (`eval-improve/`, `draft-skill/`, `retire-skill/`, `eval-guidance-improve/`, `retire-guidance/`) |

`session_costs.jsonl`, `owner_messages.jsonl` and the routine fire ledger are ledgers,
not dumps: append, never rewrite. A missing optional dump builds as empty. Never paste a
credential into a dump.

## Cost and benefit

`build.py` writes two datasets for the Spend and use group's cost panel. A week runs Monday
17:00 UTC to the next Monday and is labeled by its start date; the first is set by
`COST_START`.

- `cost_benefit_weeks`: per week, plan eval runs (`run_count`, `run_points_est` from their
  dollars at the eval rate, and `run_meter_points`, the meter's own movement during skill eval
  runs, kept for reference and never shown: whole-point ticks of the whole account, never
  recorded for guidance eval runs), API-billed eval dollars (`api_usd`,
  from `results/` summaries whose `usage.reasons.meter` is the harness's "API-billed run"
  text), scheduled-task points (`sched_points`, below), the allowance total (`total_points`,
  eval runs plus scheduled tasks, null while `sched_points` is; API credit never joins it),
  development (`dev_usd`, `dev_points`, `dev_estimated`: project threads, kept out of every
  system figure), loop changes merged, real-work reach and owner messages. `verdicts` is the
  current count of decided skill and guidance verdicts, on the latest week only.
- `cost_benefit_summary`: what the system used per decided verdict (allowance points, API
  credit dollars), scheduled tasks a week, decision yield, real-work reach, the Dec 15 bars
  (`bar_changes`, `bar_build`, and `bar_verdict` from Dec 16) and the display rates
  (`eval_usd_per_point`, `sched_usd_per_point`, `thread_usd_per_point`). Each row has a
  `group`: `system`, or `development` for `dev_points`, `bar_build` and
  `thread_usd_per_point`, which the page shows in its own Development panel.
- `routines` rows for scheduled tasks also carry `runs_per_week`, `points_per_run`,
  `points_per_week`, `in_loop` and `lane` (`eval_cap` for the eval runner, whose spend is in eval
  runs), most expensive first; a task with no recorded run on its current model reads null.

With `--spend <file>`, `build.py` also writes the weeks' totals in the shape of
`spend/weekly.json` (`spend_file` in `explorer/schema.json`): per week `eval_runs`,
`plan_meter_points`, `run_usd`, `scheduled_usd`, `api_usd` and `thread_spend_usd`, and one
`total` (`since`, `usd`, `run_usd`, `scheduled_usd`, `scheduled_since`, `api_usd`,
`thread_spend_usd`, `verdicts`, `cost_per_verdict`: `usd` is the system's use, the eval run,
scheduled-task and API columns summed, never development's `thread_spend_usd`), at full
precision, `rates` (the display rates below) and `plan` when `site.json` names one.
`loop_jobs` (`as_of`, `points_per_week`, `usd_per_week`) is the loop's own automatic jobs'
weekly meter use from `scripts/automatic_spend.py`, over `inputs/triggers.json`, the
`ROUTINE_FIRES_LEDGER` fires and `--workflows-root`; it is left out when either is unset (the
allowance guard then refuses evals rather than guess), or when an in-loop task's rate cannot be read.
An in-loop task with no fire on its current model yet is priced at its dearest recorded fire, a
task never costed at all at the dearest in-loop fire; tasks scheduled on the owner's local machine are not counted; and
`scripts/explorer_public.py` never copies it. No
session or thread row goes in. At `spend/weekly.json` on the results branch,
`scripts/explorer_public.py` copies it into the public document's `spend` (when
`evals/public-export.yml` sets `include_spend`), and the public Spend and use group
shows it. A document without `spend` hides that panel.

The Changes group's fixture requests come from `fixture_queue` in the `explorer`
dataset (all issue and PR numbers are in skills-evals); no separate dataset
carries them.

### Scheduled tasks, and development apart

Scheduled-task spend is the system's: `scripts/automatic_spend.py` over `inputs/triggers.json`,
the fire ledger and `--workflows-root` gives each task's runs a week (its cron, or its firing
workflow's) and its median run cost on its current model. A week's `sched_points` is the sum
over the tasks with a measured cost (lane `meter`; the eval runner's spend is already in eval
runs), at `scheduled_task_usd_per_point`, from the week of the ledger's first recorded run
(earlier weeks read as no value) and for the current week's elapsed part only. It is an
estimate at today's schedules, not a count of past runs: the ledger sees only each task's last
run per refresh. Tasks not in `config/routines.json` are not read.

Project threads are development (Adam building and refining the system, 2026-11-17): never in
a system total, a per-verdict figure or the weekly system table. Their spend is attributed
from `session_costs.jsonl`: the rise in a session's cumulative cost between two samples is
spread evenly over the time between them, and cost before its first sample is spread from the
session's creation, which marks the week estimated. A project-made scheduled task runs as a
project thread; its session is left out of development when the fire ledger holds that
session id, and a run the ledger missed stays in development.

### Points, not dollars, for allowance spend

Both pages show spend drawn from the weekly Max allowance (eval runs fired by routines,
scheduled tasks, and development apart) only as approximate points, marked "≈" with the rate
in a tooltip; spend paid from the monthly API credit (API-billed eval runs) stays in dollars
and never joins a points total. The rates:

- **Eval runs**: `eval_usd_per_point` in [`evals/points.yml`](../evals/points.yml), measured on
  quiet nights when eval runs were the only use. It is the only place a display rate is
  written; `build.py` exits with the reason when it is missing or not positive.
- **Scheduled tasks**: `scheduled_task_usd_per_point` in the same file. No direct measurement is
  possible (whole-point meter ticks, and a ledger that misses runs), so it is the eval run rate,
  the closest measured one; the page's tooltip says so.
- **Development (project threads)**: derived on every refresh by `thread_usd_per_point`: each
  complete week's account meter reading less that week's eval and scheduled-task points, against
  the week's thread dollars,
  summed over the weeks. The meter also counts use outside the project, so development points are
  an upper bound. With no reading yet there is no rate, and development points read as no value.

The rates travel in `spend/weekly.json` `rates` to the public document, where
`explorer/src/core/points.js` converts every allowance figure. The allowance guard does not
read `evals/points.yml`: it charges eval runs at `evals/budget.yml` `points_per_usd`.

## What stays hand-maintained, and why

Everything else comes from a read. These lists are in `config/` because no
source holds them:

| Config | Why no read can supply it |
|---|---|
| `snapshots.json` `cleanup` | A fixed list agreed once. Only items marked `waiting_on_you` are read, into the waiting list; the page has no cleanup table |
| `snapshots.json` `waiting_manual` | Asks that exist only in a conversation. Each drops automatically once its link reads closed or merged in `link_states.json` |
| `routines.json` | Each routine's plain-English `what`, `schedule` and `note`, and its `added` date (`YYYY-MM-DD`): a routine with `expect_every_hours` that has never run reads Late once twice that interval has passed since it. Last run, next run, result and health are read |
| `roster.json` | Plain-English `why` per model and the models just dropped. The list itself is read from `evals/roster.yml` |
| `site.json` | Owner names, the project's thread link prefix, its channel id, title overrides, and the repos the refresh reads: `run_console_repos`, `loop_pr_repos`, `environment_review_repos`, `extra_workflows` |

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
3. Run one refresh by hand, then schedule `tasks/refresh.md` every 24 hours (7:29 AM ET; `REFRESH_INTERVAL_HOURS` in `build.py`).
4. The page's words are in `explorer/src/core/strings.js` (shared) and
   `explorer/src/private/strings.js` (this page only); rebuild after editing.
