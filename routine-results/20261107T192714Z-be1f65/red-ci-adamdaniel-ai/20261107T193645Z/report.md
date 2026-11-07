# Eval report: red-ci-adamdaniel-ai

- Timestamp: 20261107T193645Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261107T192714Z-be1f65; started 2026-11-07T19:36:45Z, ended 2026-11-07T19:39:23Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.64 to 0.65, from 13 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.76 over 12 call(s); agent $0.59, judge $0.17, guard $0.00; last agent call $0.09

## Fixture: paths-required (n=3)

- Prompt: A docs-only PR is stuck BLOCKED waiting for the `test` check to report. Fix the workflow so it stops blocking those PRs but still only does the site work when the site changed.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 3 | 0 | 2/3 | 9.2 (9.0 to 9.5, 3 judged) | 0.1056 / 0.3169 |
| without_skill | 3 | 0 | 2/3 | 9.1 (9.0 to 9.3, 3 judged) | 0.0900 / 0.2699 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1056 / 0.0922 | 0.0900 / 0.0892 | +0.0157 | +0.0029 |
| num_turns | 5.3 / 5 | 5 / 5 | +0.3 | 0 |
| duration_ms | 18838 / 18964 | 17885 / 18027 | +953 | +937 |
| input_tokens | 10 / 10 | 10 / 10 | 0 | 0 |
| output_tokens | 1654.3 / 1654 | 1538.7 / 1537 | +115.7 | +117 |
| cache_creation_input_tokens | 17917.3 / 14456 | 14224.7 / 14041 | +3692.7 | +415 |
| cache_read_input_tokens | 174009.7 / 177451 | 176586.3 / 176589 | -2576.7 | +862 |
| tool_errors | 1 / 1 | 0.7 / 1 | +0.3 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| no-paths-filter | 3/3 | 3/3 |
| still-gated | 0/3 | 0/3 |
| site-untouched | 3/3 | 3/3 |
