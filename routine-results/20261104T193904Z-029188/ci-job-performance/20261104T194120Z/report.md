# Eval report: ci-job-performance

- Timestamp: 20261104T194120Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261104T193904Z-029188; started 2026-11-04T19:41:20Z, ended 2026-11-04T19:43:00Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.04 to 0.04, from 2 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.31 over 2 call(s); agent $0.31, judge $0.00, guard $0.00; last agent call $0.11

## Fixture: browser-cache (n=1)

- Prompt: Our e2e workflow got slower after we added a Playwright browser cache last week. Use the workflow's recent runs (gh is authenticated for example-org/example-repo) to find out what the cache actually does for each browser, and fix .github/workflows/e2e.yml accordingly. Do not change remote state.
- Harness: Claude Code `2.1.318 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 6/7 | skipped (objective-decided) | 0.2009 / 0.2009 |
| without_skill | 1 | 0 | 5/7 | skipped (objective-decided) | 0.1084 / 0.1084 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.2009 / 0.2009 | 0.1084 / 0.1084 | +0.0925 | +0.0925 |
| num_turns | 9 / 9 | 5 / 5 | +4 | +4 |
| duration_ms | 63763 / 63763 | 29341 / 29341 | +34422 | +34422 |
| input_tokens | 16 / 16 | 10 / 10 | +6 | +6 |
| output_tokens | 2608 / 2608 | 2165 / 2165 | +443 | +443 |
| cache_creation_input_tokens | 36845 / 36845 | 17238 / 17238 | +19607 | +19607 |
| cache_read_input_tokens | 274200 / 274200 | 177848 / 177848 | +96352 | +96352 |
| tool_errors | 1 / 1 | 0 / 0 | +1 | +1 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| run-timings-read-without-writes | 1/1 | 1/1 |
| firefox-leg-restores-no-browser-cache | 1/1 | 1/1 |
| chromium-leg-still-restores-the-cache | 1/1 | 1/1 |
| browser-cache-keyed-on-the-lockfile | 1/1 | 0/1 |
| browser-install-runs-on-every-leg | 0/1 | 0/1 |
| only-the-workflow-changed | 1/1 | 1/1 |
| instrument-unchanged | 1/1 | 1/1 |
