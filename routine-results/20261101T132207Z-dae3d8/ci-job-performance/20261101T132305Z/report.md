# Eval report: ci-job-performance

- Timestamp: 20261101T132305Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261101T132207Z-dae3d8; started 2026-11-01T13:23:05Z, ended 2026-11-01T13:24:13Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.85 to 0.85, from 2 snapshots

## Fixture: browser-cache (n=1)

- Prompt: Our e2e workflow got slower after we added a Playwright browser cache last week. Use the workflow's recent runs (gh is authenticated for example-org/example-repo) to find out what the cache actually does for each browser, and fix .github/workflows/e2e.yml accordingly. Do not change remote state.
- Harness: Claude Code `2.1.316 (Claude Code)`; models used: with_skill=claude-haiku-5-5, claude-sonnet-5-5; without_skill=claude-haiku-5-5, claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 6/7 | skipped (objective-decided) | 0.1423 / 0.1423 |
| without_skill | 1 | 0 | 5/7 | skipped (objective-decided) | 0.0951 / 0.0951 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1423 / 0.1423 | 0.0951 / 0.0951 | +0.0473 | +0.0473 |
| num_turns | 8 / 8 | 5 / 5 | +3 | +3 |
| duration_ms | 40782 / 40782 | 20677 / 20677 | +20105 | +20105 |
| input_tokens | 14 / 14 | 10 / 10 | +4 | +4 |
| output_tokens | 2567 / 2567 | 1670 / 1670 | +897 | +897 |
| cache_creation_input_tokens | 23020 / 23020 | 14870 / 14870 | +8150 | +8150 |
| cache_read_input_tokens | 244330 / 244330 | 187291 / 187291 | +57039 | +57039 |
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
