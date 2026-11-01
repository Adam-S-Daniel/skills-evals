# Eval report: ci-job-performance

- Timestamp: 20261101T211509Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261101T211416Z-706447; started 2026-11-01T21:15:09Z, ended 2026-11-01T21:16:36Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.93 to 0.93, from 4 snapshots

## Fixture: browser-cache (n=1)

- Prompt: Our e2e workflow got slower after we added a Playwright browser cache last week. Use the workflow's recent runs (gh is authenticated for example-org/example-repo) to find out what the cache actually does for each browser, and fix .github/workflows/e2e.yml accordingly. Do not change remote state.
- Harness: Claude Code `2.1.316 (Claude Code)`; models used: with_skill=claude-haiku-5-5, claude-sonnet-5-5; without_skill=claude-haiku-5-5, claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 5/7 | 4.6 (4.6 to 4.6, 1 judged) | 0.1342 / 0.1342 |
| without_skill | 1 | 0 | 5/7 | 5.8 (5.8 to 5.8, 1 judged) | 0.0994 / 0.0994 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1342 / 0.1342 | 0.0994 / 0.0994 | +0.0349 | +0.0349 |
| num_turns | 8 / 8 | 6 / 6 | +2 | +2 |
| duration_ms | 29228 / 29228 | 27816 / 27816 | +1412 | +1412 |
| input_tokens | 14 / 14 | 10 / 10 | +4 | +4 |
| output_tokens | 2206 / 2206 | 2167 / 2167 | +39 | +39 |
| cache_creation_input_tokens | 21927 / 21927 | 14716 / 14716 | +7211 | +7211 |
| cache_read_input_tokens | 243158 / 243158 | 186916 / 186916 | +56242 | +56242 |
| tool_errors | 0 / 0 | 0 / 0 | 0 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| run-timings-read-without-writes | 1/1 | 1/1 |
| firefox-leg-restores-no-browser-cache | 1/1 | 1/1 |
| chromium-leg-still-restores-the-cache | 1/1 | 1/1 |
| browser-cache-keyed-on-the-lockfile | 0/1 | 0/1 |
| browser-install-runs-on-every-leg | 0/1 | 0/1 |
| only-the-workflow-changed | 1/1 | 1/1 |
| instrument-unchanged | 1/1 | 1/1 |
