# Eval report: ci-job-performance

- Timestamp: 20261107T194847Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261107T193800Z-091c02; started 2026-11-07T19:48:47Z, ended 2026-11-07T19:51:33Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.65 to 0.65, from 6 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.76 over 6 call(s); agent $0.76, judge $0.00, guard $0.00; last agent call $0.11

## Fixture: browser-cache (n=3)

- Prompt: Our e2e workflow got slower after we added a Playwright browser cache last week. Use the workflow's recent runs (gh is authenticated for example-org/example-repo) to find out what the cache actually does for each browser, and fix .github/workflows/e2e.yml accordingly. Do not change remote state.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 3 | 0 | 6/7 | skipped (objective-decided) | 0.1457 / 0.4372 |
| without_skill | 3 | 0 | 5/7 | skipped (objective-decided) | 0.1088 / 0.3265 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1457 / 0.1461 | 0.1088 / 0.1079 | +0.0369 | +0.0382 |
| num_turns | 7.3 / 7 | 5.7 / 6 | +1.7 | +1 |
| duration_ms | 28147.3 / 24707 | 23023 / 23473 | +5124.3 | +1234 |
| input_tokens | 12.7 / 12 | 10 / 10 | +2.7 | +2 |
| output_tokens | 2335 / 2248 | 2189.3 / 2220 | +145.7 | +28 |
| cache_creation_input_tokens | 25595 / 24177 | 17298.7 / 17008 | +8296.3 | +7169 |
| cache_read_input_tokens | 199890.3 / 189200 | 177279.7 / 176587 | +22610.7 | +12613 |
| tool_errors | 0.3 / 0 | 0 / 0 | +0.3 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| run-timings-read-without-writes | 3/3 | 3/3 |
| firefox-leg-restores-no-browser-cache | 3/3 | 3/3 |
| chromium-leg-still-restores-the-cache | 3/3 | 3/3 |
| browser-cache-keyed-on-the-lockfile | 3/3 | 0/3 |
| browser-install-runs-on-every-leg | 0/3 | 0/3 |
| only-the-workflow-changed | 3/3 | 3/3 |
| instrument-unchanged | 3/3 | 3/3 |
