# Eval report: vendor-release-impact-issues

- Timestamp: 20261107T071808Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261107T071523Z-3e6215; started 2026-11-07T07:18:08Z, ended 2026-11-07T07:19:07Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.35 to 0.35, from 2 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.30 over 2 call(s); agent $0.30, judge $0.00, guard $0.00; last agent call $0.13

## Fixture: stamps-skip-quotes (n=1)

- Prompt: Review ExampleCLI's release notes in `vendor/` against this repository and draft the GitHub issues you would open for the changes that affect it. Every ExampleCLI version your issues mention must carry that release's publish time from `vendor/releases.json`. Write each issue to `issues/<NN>-<slug>.md`, with the issue title as the first line (`# <title>`) and the body below it. Do not open real issues.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 4/5 | skipped (objective-decided) | 0.1719 / 0.1719 |
| without_skill | 1 | 0 | 3/5 | skipped (objective-decided) | 0.1313 / 0.1313 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1719 / 0.1719 | 0.1313 / 0.1313 | +0.0406 | +0.0406 |
| num_turns | 6 / 6 | 4 / 4 | +2 | +2 |
| duration_ms | 33356 / 33356 | 21647 / 21647 | +11709 | +11709 |
| input_tokens | 10 / 10 | 8 / 8 | +2 | +2 |
| output_tokens | 4144 / 4144 | 2366 / 2366 | +1778 | +1778 |
| cache_creation_input_tokens | 29381 / 29381 | 23877 / 23877 | +5504 | +5504 |
| cache_read_input_tokens | 129029 / 129029 | 121173 / 121173 | +7856 | +7856 |
| tool_errors | 0 / 0 | 0 / 0 | 0 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| quotes-kept-verbatim | 1/1 | 0/1 |
| quoted-text-unstamped | 0/1 | 0/1 |
| titles-unstamped | 1/1 | 1/1 |
| prose-versions-stamped | 1/1 | 1/1 |
| seed-repo-unchanged | 1/1 | 1/1 |
