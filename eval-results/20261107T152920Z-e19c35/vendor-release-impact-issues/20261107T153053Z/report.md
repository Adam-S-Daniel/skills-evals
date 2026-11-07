# Eval report: vendor-release-impact-issues

- Timestamp: 20261107T153053Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261107T152920Z-e19c35; started 2026-11-07T15:30:53Z, ended 2026-11-07T15:37:21Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.49 to 0.5, from 7 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $2.40 over 6 call(s); agent $2.40, judge $0.00, guard $0.00; last agent call $0.33

## Fixture: stamps-skip-quotes (n=3)

- Prompt: Review ExampleCLI's release notes in `vendor/` against this repository and draft the GitHub issues you would open for the changes that affect it. Every ExampleCLI version your issues mention must carry that release's publish time from `vendor/releases.json`. Write each issue to `issues/<NN>-<slug>.md`, with the issue title as the first line (`# <title>`) and the body below it. Do not open real issues.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-opus-5-5; without_skill=claude-opus-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 3 | 0 | 4/5 | skipped (objective-decided) | 0.4363 / 1.3089 |
| without_skill | 3 | 0 | 2.3/5 | skipped (objective-decided) | 0.3630 / 1.0891 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.4363 / 0.4425 | 0.3630 / 0.3463 | +0.0733 | +0.0963 |
| num_turns | 8 / 8 | 5.7 / 5 | +2.3 | +3 |
| duration_ms | 65825.7 / 59670 | 60136.7 / 59793 | +5689 | -123 |
| input_tokens | 14.7 / 16 | 11.3 / 10 | +3.3 | +6 |
| output_tokens | 5950 / 6016 | 5060.7 / 4780 | +889.3 | +1236 |
| cache_creation_input_tokens | 33785.7 / 33809 | 27970.7 / 27268 | +5815 | +6541 |
| cache_read_input_tokens | 234778.7 / 262411 | 190049.7 / 162560 | +44729 | +99851 |
| tool_errors | 0 / 0 | 0 / 0 | 0 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| quotes-kept-verbatim | 3/3 | 0/3 |
| quoted-text-unstamped | 0/3 | 1/3 |
| titles-unstamped | 3/3 | 0/3 |
| prose-versions-stamped | 3/3 | 3/3 |
| seed-repo-unchanged | 3/3 | 3/3 |
