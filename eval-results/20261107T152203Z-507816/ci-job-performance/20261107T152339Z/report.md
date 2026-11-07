# Eval report: ci-job-performance

- Timestamp: 20261107T152339Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261107T152203Z-507816; started 2026-11-07T15:23:39Z, ended 2026-11-07T15:31:31Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.49 to 0.49, from 6 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $3.27 over 6 call(s); agent $3.27, judge $0.00, guard $0.00; last agent call $0.59

## Fixture: browser-cache (n=3)

- Prompt: Our e2e workflow got slower after we added a Playwright browser cache last week. Use the workflow's recent runs (gh is authenticated for example-org/example-repo) to find out what the cache actually does for each browser, and fix .github/workflows/e2e.yml accordingly. Do not change remote state.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-haiku-5-5, claude-opus-5-5; without_skill=claude-haiku-5-5, claude-opus-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 3 | 0 | 6.3/7 | skipped (objective-decided) | 0.5348 / 1.6043 |
| without_skill | 3 | 0 | 6/7 | skipped (objective-decided) | 0.5554 / 1.6662 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.5348 / 0.5048 | 0.5554 / 0.5862 | -0.0206 | -0.0814 |
| num_turns | 12.3 / 12 | 12 / 12 | +0.3 | 0 |
| duration_ms | 71095.3 / 74994 | 81074.3 / 69465 | -9979 | +5529 |
| input_tokens | 24 / 24 | 22.7 / 22 | +1.3 | +2 |
| output_tokens | 5625.3 / 5817 | 6449 / 6266 | -823.7 | -449 |
| cache_creation_input_tokens | 40346.7 / 37229 | 40740.7 / 42789 | -394 | -5560 |
| cache_read_input_tokens | 477514.3 / 482449 | 485744.7 / 464200 | -8230.3 | +18249 |
| tool_errors | 0.7 / 1 | 0.7 / 1 | 0 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| run-timings-read-without-writes | 3/3 | 3/3 |
| firefox-leg-restores-no-browser-cache | 3/3 | 3/3 |
| chromium-leg-still-restores-the-cache | 3/3 | 3/3 |
| browser-cache-keyed-on-the-lockfile | 3/3 | 3/3 |
| browser-install-runs-on-every-leg | 1/3 | 0/3 |
| only-the-workflow-changed | 3/3 | 3/3 |
| instrument-unchanged | 3/3 | 3/3 |
