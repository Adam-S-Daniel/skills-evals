# Eval report: ci-job-performance

- Timestamp: 20261107T193935Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261107T193800Z-091c02; started 2026-11-07T19:39:35Z, ended 2026-11-07T19:48:46Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.65 to 0.65, from 6 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $3.38 over 6 call(s); agent $3.38, judge $0.00, guard $0.00; last agent call $0.58

## Fixture: browser-cache (n=3)

- Prompt: Our e2e workflow got slower after we added a Playwright browser cache last week. Use the workflow's recent runs (gh is authenticated for example-org/example-repo) to find out what the cache actually does for each browser, and fix .github/workflows/e2e.yml accordingly. Do not change remote state.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-haiku-5-5, claude-opus-5-5; without_skill=claude-haiku-5-5, claude-opus-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 3 | 0 | 6.7/7 | skipped (objective-decided) | 0.5330 / 1.5990 |
| without_skill | 3 | 0 | 6/7 | skipped (objective-decided) | 0.5938 / 1.7813 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.5330 / 0.5278 | 0.5938 / 0.5844 | -0.0608 | -0.0565 |
| num_turns | 12 / 12 | 11.3 / 11 | +0.7 | +1 |
| duration_ms | 80874.3 / 79882 | 98354 / 97259 | -17479.7 | -17377 |
| input_tokens | 24 / 24 | 23.3 / 24 | +0.7 | 0 |
| output_tokens | 5865.3 / 5430 | 6880 / 6977 | -1014.7 | -1547 |
| cache_creation_input_tokens | 39608.7 / 40791 | 43642.7 / 42503 | -4034 | -1712 |
| cache_read_input_tokens | 477629 / 477461 | 510228.7 / 500307 | -32599.7 | -22846 |
| tool_errors | 0.3 / 0 | 0 / 0 | +0.3 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| run-timings-read-without-writes | 3/3 | 3/3 |
| firefox-leg-restores-no-browser-cache | 3/3 | 3/3 |
| chromium-leg-still-restores-the-cache | 3/3 | 3/3 |
| browser-cache-keyed-on-the-lockfile | 3/3 | 3/3 |
| browser-install-runs-on-every-leg | 2/3 | 0/3 |
| only-the-workflow-changed | 3/3 | 3/3 |
| instrument-unchanged | 3/3 | 3/3 |
