# Eval report: ci-job-performance

- Timestamp: 20261026T211625Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261026T211329Z-fdfe3e; started 2026-10-26T21:16:25Z, ended 2026-10-26T21:18:25Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): five_hour 0.18 to 0.18, seven_day 0.05 to 0.05, from 4 snapshots

## Fixture: browser-cache (n=1)

- Prompt: Our e2e workflow got slower after we added a Playwright browser cache last week. Use the workflow's recent runs (gh is authenticated for example-org/example-repo) to find out what the cache actually does for each browser, and fix .github/workflows/e2e.yml accordingly. Do not change remote state.
- Harness: Claude Code `2.1.310 (Claude Code)`; models used: with_skill=claude-haiku-5-5, claude-sonnet-5-5; without_skill=claude-haiku-5-5, claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 6/7 | 5.6 (5.6 to 5.6, 1 judged) | 0.1579 / 0.1579 |
| without_skill | 1 | 0 | 6/7 | 5.6 (5.6 to 5.6, 1 judged) | 0.1033 / 0.1033 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1579 / 0.1579 | 0.1033 / 0.1033 | +0.0546 | +0.0546 |
| num_turns | 9 / 9 | 5 / 5 | +4 | +4 |
| duration_ms | 58175 / 58175 | 27930 / 27930 | +30245 | +30245 |
| input_tokens | 14 / 14 | 10 / 10 | +4 | +4 |
| output_tokens | 3193 / 3193 | 2376 / 2376 | +817 | +817 |
| cache_creation_input_tokens | 24118 / 24118 | 15179 / 15179 | +8939 | +8939 |
| cache_read_input_tokens | 292919 / 292919 | 186227 / 186227 | +106692 | +106692 |
| tool_errors | 1 / 1 | 0 / 0 | +1 | +1 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| run-timings-read-without-writes | 1/1 | 1/1 |
| firefox-leg-restores-no-browser-cache | 1/1 | 1/1 |
| chromium-leg-still-restores-the-cache | 1/1 | 1/1 |
| browser-cache-keyed-on-the-lockfile | 1/1 | 1/1 |
| browser-install-runs-on-every-leg | 0/1 | 0/1 |
| only-the-workflow-changed | 1/1 | 1/1 |
| instrument-unchanged | 1/1 | 1/1 |
