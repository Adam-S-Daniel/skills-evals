# Eval report: platform-release-and-bump

- Timestamp: 20261107T201306Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261107T200304Z-03749f; started 2026-11-07T20:13:06Z, ended 2026-11-07T20:19:06Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.67 to 0.67, from 12 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $1.70 over 12 call(s); agent $1.14, judge $0.56, guard $0.00; last agent call $0.18

## Fixture: platform-release-and-bump (n=3)

- Prompt: Bump this consumer to platform v0.1.104.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 3 | 0 | 10/10 | 7.3 (6.0 to 8.5, 3 judged) | 0.1972 / 0.5916 |
| without_skill | 3 | 0 | 10/10 | 7.7 (6.4 to 8.5, 3 judged) | 0.1818 / 0.5453 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1972 / 0.2008 | 0.1818 / 0.1827 | +0.0154 | +0.0181 |
| num_turns | 11.7 / 11 | 10 / 10 | +1.7 | +1 |
| duration_ms | 44719.7 / 47304 | 45615 / 42026 | -895.3 | +5278 |
| input_tokens | 20.7 / 20 | 19.3 / 18 | +1.3 | +2 |
| output_tokens | 3217.7 / 3198 | 3270.3 / 3368 | -52.7 | -170 |
| cache_creation_input_tokens | 30783.3 / 28623 | 26778 / 28206 | +4005.3 | +417 |
| cache_read_input_tokens | 418396.3 / 404887 | 419055 / 396797 | -658.7 | +8090 |
| tool_errors | 0.3 / 0 | 0 / 0 | +0.3 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| canonical-verifier | 3/3 | 3/3 |
| refs-on-release | 3/3 | 3/3 |
| resolved-revision | 3/3 | 3/3 |
| added-caller | 3/3 | 3/3 |
| retired-caller | 3/3 | 3/3 |
| gem-files-present | 3/3 | 3/3 |
| no-pin-comments | 3/3 | 3/3 |
| no-gh-write | 3/3 | 3/3 |
| verifier-digest | 3/3 | 3/3 |
| instrument-unchanged | 3/3 | 3/3 |
