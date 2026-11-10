# Eval report: vendor-release-impact-issues

- Timestamp: 20261110T061438Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261110T061311Z-9a4ee0; started 2026-11-10T06:14:38Z, ended 2026-11-10T06:17:27Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.19 to 0.19, from 6 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $1.01 over 6 call(s); agent $0.70, judge $0.31, guard $0.00; last agent call $0.19

## Fixture: stamps-skip-quotes (n=3)

- Prompt: Review ExampleCLI's release notes in `vendor/` against this repository and draft the GitHub issues you would open for the changes that affect it. Every ExampleCLI version your issues mention must carry that release's publish time from `vendor/releases.json`. Write each issue to `issues/<NN>-<slug>.md`, with the issue title as the first line (`# <title>`) and the body below it. Do not open real issues.
- Harness: Claude Code `2.1.322 (Claude Code)`; models used: without_skill=claude-opus-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| without_skill | 3 | 0 | 3.3/5 | 6.7 (5.0 to 8.3, 3 judged) | 0.2332 / 0.6995 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did):

| Metric (mean / median) | without_skill |
| --- | --- |
| cost_usd | 0.2332 / 0.1934 |
| num_turns | 5 / 5 |
| duration_ms | 41339.7 / 41902 |
| input_tokens | 10 / 10 |
| output_tokens | 4106.7 / 4006 |
| cache_creation_input_tokens | 23212 / 13883 |
| cache_read_input_tokens | 174621.7 / 155018 |
| tool_errors | 0 / 0 |

| Check (passed / scored) | without_skill |
| --- | --- |
| quotes-kept-verbatim | 2/3 |
| quoted-text-unstamped | 0/3 |
| titles-unstamped | 2/3 |
| prose-versions-stamped | 3/3 |
| seed-repo-unchanged | 3/3 |
