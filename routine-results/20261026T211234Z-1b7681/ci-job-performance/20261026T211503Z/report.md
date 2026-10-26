# Eval report: ci-job-performance

- Timestamp: 20261026T211503Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261026T211234Z-1b7681; started 2026-10-26T21:15:03Z, ended 2026-10-26T21:19:16Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): five_hour 0.18 to 0.19, seven_day 0.05 to 0.05, from 6 snapshots

## Fixture: browser-cache (n=3)

- Prompt: Our e2e workflow got slower after we added a Playwright browser cache last week. Use the workflow's recent runs (gh is authenticated for example-org/example-repo) to find out what the cache actually does for each browser, and fix .github/workflows/e2e.yml accordingly. Do not change remote state.
- Harness: Claude Code `2.1.310 (Claude Code)`; models used: with_skill=claude-haiku-5-5, claude-sonnet-5-5; without_skill=claude-haiku-5-5, claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 3 | 0 | 6/7 | skipped (objective-decided) | 0.1488 / 0.4464 |
| without_skill | 3 | 0 | 5/7 | skipped (objective-decided) | 0.1021 / 0.3064 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1488 / 0.1221 | 0.1021 / 0.0987 | +0.0467 | +0.0234 |
| num_turns | 9.3 / 8 | 5.7 / 6 | +3.7 | +2 |
| duration_ms | 50674.7 / 31786 | 27937.3 / 27364 | +22737.3 | +4422 |
| input_tokens | 14.7 / 12 | 10 / 10 | +4.7 | +2 |
| output_tokens | 2593.7 / 2263 | 1910.3 / 1838 | +683.3 | +425 |
| cache_creation_input_tokens | 22703 / 19141 | 16004 / 15363 | +6699 | +3778 |
| cache_read_input_tokens | 318842.3 / 239960 | 188446.7 / 186925 | +130395.7 | +53035 |
| tool_errors | 0 / 0 | 0 / 0 | 0 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| run-timings-read-without-writes | 3/3 | 3/3 |
| firefox-leg-restores-no-browser-cache | 3/3 | 3/3 |
| chromium-leg-still-restores-the-cache | 3/3 | 3/3 |
| browser-cache-keyed-on-the-lockfile | 3/3 | 0/3 |
| browser-install-runs-on-every-leg | 0/3 | 0/3 |
| only-the-workflow-changed | 3/3 | 3/3 |
| instrument-unchanged | 3/3 | 3/3 |
