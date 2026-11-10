# Eval report: ci-job-performance

- Timestamp: 20261110T025000Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261110T024753Z-7ab91f; started 2026-11-10T02:50:00Z, ended 2026-11-10T02:53:21Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.15 to 0.15, from 6 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $1.44 over 6 call(s); agent $1.12, judge $0.32, guard $0.00; last agent call $0.39

## Fixture: browser-cache (n=3)

- Prompt: Our e2e workflow got slower after we added a Playwright browser cache last week. Use the workflow's recent runs (gh is authenticated for example-org/example-repo) to find out what the cache actually does for each browser, and fix .github/workflows/e2e.yml accordingly. Do not change remote state.
- Harness: Claude Code `2.1.322 (Claude Code)`; models used: without_skill=claude-opus-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| without_skill | 3 | 0 | 5.7/7 | 5.5 (5.2 to 5.8, 3 judged) | 0.3737 / 1.1212 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did):

| Metric (mean / median) | without_skill |
| --- | --- |
| cost_usd | 0.3737 / 0.3878 |
| num_turns | 9.3 / 9 |
| duration_ms | 51222.7 / 46043 |
| input_tokens | 18 / 18 |
| output_tokens | 4281 / 3825 |
| cache_creation_input_tokens | 41655 / 39064 |
| cache_read_input_tokens | 398815.7 / 348870 |
| tool_errors | 0.7 / 1 |

| Check (passed / scored) | without_skill |
| --- | --- |
| run-timings-read-without-writes | 3/3 |
| firefox-leg-restores-no-browser-cache | 3/3 |
| chromium-leg-still-restores-the-cache | 3/3 |
| browser-cache-keyed-on-the-lockfile | 2/3 |
| browser-install-runs-on-every-leg | 0/3 |
| only-the-workflow-changed | 3/3 |
| instrument-unchanged | 3/3 |
