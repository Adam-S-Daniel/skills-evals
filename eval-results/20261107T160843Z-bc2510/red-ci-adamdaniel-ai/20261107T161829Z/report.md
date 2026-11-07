# Eval report: red-ci-adamdaniel-ai

- Timestamp: 20261107T161829Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261107T160843Z-bc2510; started 2026-11-07T16:18:29Z, ended 2026-11-07T16:21:22Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.53 to 0.53, from 12 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.78 over 12 call(s); agent $0.59, judge $0.19, guard $0.00; last agent call $0.09

## Fixture: paths-required (n=3)

- Prompt: A docs-only PR is stuck BLOCKED waiting for the `test` check to report. Fix the workflow so it stops blocking those PRs but still only does the site work when the site changed.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 3 | 0 | 2/3 | 9.0 (8.7 to 9.4, 3 judged) | 0.1069 / 0.3208 |
| without_skill | 3 | 0 | 2/3 | 9.0 (9.0 to 9.0, 3 judged) | 0.0907 / 0.2720 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1069 / 0.0964 | 0.0907 / 0.0903 | +0.0163 | +0.0061 |
| num_turns | 5.3 / 5 | 5 / 5 | +0.3 | 0 |
| duration_ms | 20532.7 / 19162 | 19224 / 18780 | +1308.7 | +382 |
| input_tokens | 10 / 10 | 10 / 10 | 0 | 0 |
| output_tokens | 1763 / 1648 | 1656.3 / 1618 | +106.7 | +30 |
| cache_creation_input_tokens | 17974.7 / 14660 | 14109.7 / 14109 | +3865 | +551 |
| cache_read_input_tokens | 173879.3 / 177323 | 176609.7 / 176666 | -2730.3 | +657 |
| tool_errors | 0.3 / 0 | 0.3 / 0 | 0 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| no-paths-filter | 3/3 | 3/3 |
| still-gated | 0/3 | 0/3 |
| site-untouched | 3/3 | 3/3 |
