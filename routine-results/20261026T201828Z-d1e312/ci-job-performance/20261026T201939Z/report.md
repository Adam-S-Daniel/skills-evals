# Eval report: ci-job-performance

- Timestamp: 20261026T201939Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261026T201828Z-d1e312; started 2026-10-26T20:19:39Z, ended 2026-10-26T20:25:07Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): five_hour 0.11 to 0.12, seven_day 0.03 to 0.04, from 13 snapshots

## Fixture: browser-cache (n=3)

- Prompt: Our e2e workflow got slower after we added a Playwright browser cache last week. Use the workflow's recent runs (gh is authenticated for example-org/example-repo) to find out what the cache actually does for each browser, and fix .github/workflows/e2e.yml accordingly. Do not change remote state.
- Harness: Claude Code `2.1.310 (Claude Code)`; models used: with_skill=claude-haiku-5-5, claude-sonnet-5-5; without_skill=claude-haiku-5-5, claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 3 | 0 | 3/7 | 5.3 (4.8 to 5.8, 3 judged) | 0.1363 / 0.4089 |
| without_skill | 3 | 0 | 3/7 | 5.2 (4.6 to 5.6, 3 judged) | 0.0987 / 0.2961 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1363 / 0.1392 | 0.0987 / 0.0997 | +0.0376 | +0.0396 |
| num_turns | 8.7 / 9 | 5.3 / 5 | +3.3 | +4 |
| duration_ms | 44493.3 / 45865 | 35162.3 / 35791 | +9331 | +10074 |
| input_tokens | 12.7 / 12 | 10 / 10 | +2.7 | +2 |
| output_tokens | 2464 / 2388 | 2006.7 / 1946 | +457.3 | +442 |
| cache_creation_input_tokens | 21463.7 / 22695 | 14960 / 14925 | +6503.7 | +7770 |
| cache_read_input_tokens | 256508.7 / 245625 | 186508 / 186318 | +70000.7 | +59307 |
| tool_errors | 0.7 / 1 | 0 / 0 | +0.7 | +1 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| run-timings-read-without-writes | 3/3 | 3/3 |
| firefox-leg-restores-no-browser-cache | 0/3 | 0/3 |
| chromium-leg-still-restores-the-cache | 0/3 | 0/3 |
| browser-cache-keyed-on-the-lockfile | 0/3 | 0/3 |
| browser-install-runs-on-every-leg | 0/3 | 0/3 |
| only-the-workflow-changed | 3/3 | 3/3 |
| instrument-unchanged | 3/3 | 3/3 |
