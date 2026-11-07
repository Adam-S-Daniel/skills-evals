# Eval report: ci-job-performance

- Timestamp: 20261107T072356Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261107T072233Z-e1ad88; started 2026-11-07T07:23:56Z, ended 2026-11-07T07:24:53Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.35 to 0.35, from 2 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.28 over 2 call(s); agent $0.28, judge $0.00, guard $0.00; last agent call $0.11

## Fixture: browser-cache (n=1)

- Prompt: Our e2e workflow got slower after we added a Playwright browser cache last week. Use the workflow's recent runs (gh is authenticated for example-org/example-repo) to find out what the cache actually does for each browser, and fix .github/workflows/e2e.yml accordingly. Do not change remote state.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 6/7 | skipped (objective-decided) | 0.1734 / 0.1734 |
| without_skill | 1 | 0 | 5/7 | skipped (objective-decided) | 0.1109 / 0.1109 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1734 / 0.1734 | 0.1109 / 0.1109 | +0.0625 | +0.0625 |
| num_turns | 8 / 8 | 6 / 6 | +2 | +2 |
| duration_ms | 23891 / 23891 | 27678 / 27678 | -3787 | -3787 |
| input_tokens | 14 / 14 | 10 / 10 | +4 | +4 |
| output_tokens | 2267 / 2267 | 2046 / 2046 | +221 | +221 |
| cache_creation_input_tokens | 32042 / 32042 | 18150 / 18150 | +13892 | +13892 |
| cache_read_input_tokens | 224969 / 224969 | 178291 / 178291 | +46678 | +46678 |
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
