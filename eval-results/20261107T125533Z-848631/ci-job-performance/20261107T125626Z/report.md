# Eval report: ci-job-performance

- Timestamp: 20261107T125626Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261107T125533Z-848631; started 2026-11-07T12:56:26Z, ended 2026-11-07T12:58:11Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.43 to 0.43, from 6 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.46 over 6 call(s); agent $0.30, judge $0.16, guard $0.00; last agent call $0.10

## Fixture: browser-cache (n=3)

- Prompt: Our e2e workflow got slower after we added a Playwright browser cache last week. Use the workflow's recent runs (gh is authenticated for example-org/example-repo) to find out what the cache actually does for each browser, and fix .github/workflows/e2e.yml accordingly. Do not change remote state.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| without_skill | 3 | 0 | 5/7 | 4.7 (4.6 to 4.8, 3 judged) | 0.1004 / 0.3012 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did):

| Metric (mean / median) | without_skill |
| --- | --- |
| cost_usd | 0.1004 / 0.0986 |
| num_turns | 5.3 / 5 |
| duration_ms | 21751.3 / 21612 |
| input_tokens | 10 / 10 |
| output_tokens | 1892.7 / 1880 |
| cache_creation_input_tokens | 15647.3 / 15650 |
| cache_read_input_tokens | 188580 / 188630 |
| tool_errors | 0 / 0 |

| Check (passed / scored) | without_skill |
| --- | --- |
| run-timings-read-without-writes | 3/3 |
| firefox-leg-restores-no-browser-cache | 3/3 |
| chromium-leg-still-restores-the-cache | 3/3 |
| browser-cache-keyed-on-the-lockfile | 0/3 |
| browser-install-runs-on-every-leg | 0/3 |
| only-the-workflow-changed | 3/3 |
| instrument-unchanged | 3/3 |
