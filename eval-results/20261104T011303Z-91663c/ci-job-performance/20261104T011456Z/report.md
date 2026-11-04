# Eval report: ci-job-performance

- Timestamp: 20261104T011456Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261104T011303Z-91663c; started 2026-11-04T01:14:56Z, ended 2026-11-04T01:16:01Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.84 to 0.84, from 2 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.30 over 2 call(s); agent $0.30, judge $0.00, guard $0.00; last agent call $0.11

## Fixture: browser-cache (n=1)

- Prompt: Our e2e workflow got slower after we added a Playwright browser cache last week. Use the workflow's recent runs (gh is authenticated for example-org/example-repo) to find out what the cache actually does for each browser, and fix .github/workflows/e2e.yml accordingly. Do not change remote state.
- Harness: Claude Code `2.1.318 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 6/7 | skipped (objective-decided) | 0.1925 / 0.1925 |
| without_skill | 1 | 0 | 5/7 | skipped (objective-decided) | 0.1083 / 0.1083 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1925 / 0.1925 | 0.1083 / 0.1083 | +0.0842 | +0.0842 |
| num_turns | 9 / 9 | 6 / 6 | +3 | +3 |
| duration_ms | 36381 / 36381 | 22716 / 22716 | +13665 | +13665 |
| input_tokens | 16 / 16 | 10 / 10 | +6 | +6 |
| output_tokens | 2885 / 2885 | 2213 / 2213 | +672 | +672 |
| cache_creation_input_tokens | 34219 / 34219 | 17092 / 17092 | +17127 | +17127 |
| cache_read_input_tokens | 267308 / 267308 | 177561 / 177561 | +89747 | +89747 |
| tool_errors | 0 / 0 | 0 / 0 | 0 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| run-timings-read-without-writes | 1/1 | 1/1 |
| firefox-leg-restores-no-browser-cache | 1/1 | 1/1 |
| chromium-leg-still-restores-the-cache | 1/1 | 1/1 |
| browser-cache-keyed-on-the-lockfile | 1/1 | 0/1 |
| browser-install-runs-on-every-leg | 0/1 | 0/1 |
| only-the-workflow-changed | 1/1 | 1/1 |
| instrument-unchanged | 1/1 | 1/1 |
