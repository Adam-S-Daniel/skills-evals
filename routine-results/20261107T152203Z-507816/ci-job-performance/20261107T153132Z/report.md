# Eval report: ci-job-performance

- Timestamp: 20261107T153132Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261107T152203Z-507816; started 2026-11-07T15:31:32Z, ended 2026-11-07T15:35:53Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.49 to 0.5, from 7 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.85 over 6 call(s); agent $0.85, judge $0.00, guard $0.00; last agent call $0.11

## Fixture: browser-cache (n=3)

- Prompt: Our e2e workflow got slower after we added a Playwright browser cache last week. Use the workflow's recent runs (gh is authenticated for example-org/example-repo) to find out what the cache actually does for each browser, and fix .github/workflows/e2e.yml accordingly. Do not change remote state.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 3 | 0 | 5.7/7 | skipped (objective-decided) | 0.1755 / 0.5266 |
| without_skill | 3 | 0 | 5/7 | skipped (objective-decided) | 0.1067 / 0.3202 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1755 / 0.1855 | 0.1067 / 0.1062 | +0.0688 | +0.0793 |
| num_turns | 10 / 11 | 5 / 5 | +5 | +6 |
| duration_ms | 49579 / 49806 | 32635.3 / 33285 | +16943.7 | +16521 |
| input_tokens | 18 / 20 | 10 / 10 | +8 | +10 |
| output_tokens | 3085.7 / 3324 | 1936.3 / 1891 | +1149.3 | +1433 |
| cache_creation_input_tokens | 27998.7 / 27597 | 17377.3 / 17514 | +10621.3 | +10083 |
| cache_read_input_tokens | 326302.3 / 367372 | 178364 / 178162 | +147938.3 | +189210 |
| tool_errors | 1 / 1 | 0 / 0 | +1 | +1 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| run-timings-read-without-writes | 3/3 | 3/3 |
| firefox-leg-restores-no-browser-cache | 3/3 | 3/3 |
| chromium-leg-still-restores-the-cache | 3/3 | 3/3 |
| browser-cache-keyed-on-the-lockfile | 2/3 | 0/3 |
| browser-install-runs-on-every-leg | 0/3 | 0/3 |
| only-the-workflow-changed | 3/3 | 3/3 |
| instrument-unchanged | 3/3 | 3/3 |
