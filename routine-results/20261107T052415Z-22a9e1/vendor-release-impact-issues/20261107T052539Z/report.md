# Eval report: vendor-release-impact-issues

- Timestamp: 20261107T052539Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261107T052415Z-22a9e1; started 2026-11-07T05:25:39Z, ended 2026-11-07T05:26:56Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.34 to 0.34, from 4 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.42 over 4 call(s); agent $0.31, judge $0.11, guard $0.00; last agent call $0.13

## Fixture: stamps-skip-quotes (n=1)

- Prompt: Review ExampleCLI's release notes in `vendor/` against this repository and draft the GitHub issues you would open for the changes that affect it. Every ExampleCLI version your issues mention must carry that release's publish time from `vendor/releases.json`. Write each issue to `issues/<NN>-<slug>.md`, with the issue title as the first line (`# <title>`) and the body below it. Do not open real issues.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 4/5 | 8.9 (8.9 to 8.9, 1 judged) | 0.1854 / 0.1854 |
| without_skill | 1 | 0 | 4/5 | 5.0 (5.0 to 5.0, 1 judged) | 0.1283 / 0.1283 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1854 / 0.1854 | 0.1283 / 0.1283 | +0.0571 | +0.0571 |
| num_turns | 7 / 7 | 4 / 4 | +3 | +3 |
| duration_ms | 31895 / 31895 | 19090 / 19090 | +12805 | +12805 |
| input_tokens | 12 / 12 | 8 / 8 | +4 | +4 |
| output_tokens | 4223 / 4223 | 2222 / 2222 | +2001 | +2001 |
| cache_creation_input_tokens | 31436 / 31436 | 23496 / 23496 | +7940 | +7940 |
| cache_read_input_tokens | 174030 / 174030 | 120735 / 120735 | +53295 | +53295 |
| tool_errors | 0 / 0 | 0 / 0 | 0 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| quotes-kept-verbatim | 1/1 | 0/1 |
| quoted-text-unstamped | 0/1 | 1/1 |
| titles-unstamped | 1/1 | 1/1 |
| prose-versions-stamped | 1/1 | 1/1 |
| seed-repo-unchanged | 1/1 | 1/1 |
