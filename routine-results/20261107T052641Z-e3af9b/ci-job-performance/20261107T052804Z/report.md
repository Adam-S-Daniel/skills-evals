# Eval report: ci-job-performance

- Timestamp: 20261107T052804Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261107T052641Z-e3af9b; started 2026-11-07T05:28:04Z, ended 2026-11-07T05:28:53Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.34 to 0.34, from 2 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.27 over 2 call(s); agent $0.27, judge $0.00, guard $0.00; last agent call $0.11

## Fixture: browser-cache (n=1)

- Prompt: Our e2e workflow got slower after we added a Playwright browser cache last week. Use the workflow's recent runs (gh is authenticated for example-org/example-repo) to find out what the cache actually does for each browser, and fix .github/workflows/e2e.yml accordingly. Do not change remote state.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 6/7 | skipped (objective-decided) | 0.1658 / 0.1658 |
| without_skill | 1 | 0 | 5/7 | skipped (objective-decided) | 0.1081 / 0.1081 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1658 / 0.1658 | 0.1081 / 0.1081 | +0.0577 | +0.0577 |
| num_turns | 7 / 7 | 5 / 5 | +2 | +2 |
| duration_ms | 22264 / 22264 | 22168 / 22168 | +96 | +96 |
| input_tokens | 12 / 12 | 10 / 10 | +2 | +2 |
| output_tokens | 2012 / 2012 | 1859 / 1859 | +153 | +153 |
| cache_creation_input_tokens | 31938 / 31938 | 17895 / 17895 | +14043 | +14043 |
| cache_read_input_tokens | 179038 / 179038 | 179450 / 179450 | -412 | -412 |
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
