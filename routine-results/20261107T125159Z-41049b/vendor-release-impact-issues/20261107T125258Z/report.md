# Eval report: vendor-release-impact-issues

- Timestamp: 20261107T125258Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261107T125159Z-41049b; started 2026-11-07T12:52:58Z, ended 2026-11-07T12:54:36Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.43 to 0.43, from 6 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.39 over 6 call(s); agent $0.25, judge $0.14, guard $0.00; last agent call $0.08

## Fixture: stamps-skip-quotes (n=3)

- Prompt: Review ExampleCLI's release notes in `vendor/` against this repository and draft the GitHub issues you would open for the changes that affect it. Every ExampleCLI version your issues mention must carry that release's publish time from `vendor/releases.json`. Write each issue to `issues/<NN>-<slug>.md`, with the issue title as the first line (`# <title>`) and the body below it. Do not open real issues.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| without_skill | 3 | 0 | 3.7/5 | 7.5 (5.5 to 8.6, 3 judged) | 0.0817 / 0.2451 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did):

| Metric (mean / median) | without_skill |
| --- | --- |
| cost_usd | 0.0817 / 0.0820 |
| num_turns | 4 / 4 |
| duration_ms | 21274 / 20206 |
| input_tokens | 8 / 8 |
| output_tokens | 2097 / 2100 |
| cache_creation_input_tokens | 11680.7 / 11643 |
| cache_read_input_tokens | 139868.3 / 139897 |
| tool_errors | 0 / 0 |

| Check (passed / scored) | without_skill |
| --- | --- |
| quotes-kept-verbatim | 0/3 |
| quoted-text-unstamped | 2/3 |
| titles-unstamped | 3/3 |
| prose-versions-stamped | 3/3 |
| seed-repo-unchanged | 3/3 |
