# Eval report: ci-job-performance

- Timestamp: 20261107T111223Z
- Trials per arm: 2
- Run: billing subscription, runner routine, location cloud, id 20261107T111051Z-87fc06; started 2026-11-07T11:12:23Z, ended 2026-11-07T11:14:28Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.41 to 0.41, from 4 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.56 over 4 call(s); agent $0.56, judge $0.00, guard $0.00; last agent call $0.10

## Fixture: browser-cache (n=2)

- Prompt: Our e2e workflow got slower after we added a Playwright browser cache last week. Use the workflow's recent runs (gh is authenticated for example-org/example-repo) to find out what the cache actually does for each browser, and fix .github/workflows/e2e.yml accordingly. Do not change remote state.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 2 | 0 | 5.5/7 | skipped (objective-decided) | 0.1691 / 0.3382 |
| without_skill | 2 | 0 | 5/7 | skipped (objective-decided) | 0.1084 / 0.2169 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1691 / 0.1691 | 0.1084 / 0.1084 | +0.0607 | +0.0607 |
| num_turns | 8.5 / 8.5 | 5.5 / 5.5 | +3 | +3 |
| duration_ms | 31801.5 / 31801.5 | 25723 / 25723 | +6078.5 | +6078.5 |
| input_tokens | 14 / 14 | 10 / 10 | +4 | +4 |
| output_tokens | 2700 / 2700 | 2045.5 / 2045.5 | +654.5 | +654.5 |
| cache_creation_input_tokens | 29697 / 29697 | 17531.5 / 17531.5 | +12165.5 | +12165.5 |
| cache_read_input_tokens | 232989.5 / 232989.5 | 178406.5 / 178406.5 | +54583 | +54583 |
| tool_errors | 0.5 / 0.5 | 0 / 0 | +0.5 | +0.5 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| run-timings-read-without-writes | 2/2 | 2/2 |
| firefox-leg-restores-no-browser-cache | 2/2 | 2/2 |
| chromium-leg-still-restores-the-cache | 2/2 | 2/2 |
| browser-cache-keyed-on-the-lockfile | 1/2 | 0/2 |
| browser-install-runs-on-every-leg | 0/2 | 0/2 |
| only-the-workflow-changed | 2/2 | 2/2 |
| instrument-unchanged | 2/2 | 2/2 |
