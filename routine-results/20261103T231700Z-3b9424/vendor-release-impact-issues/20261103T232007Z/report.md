# Eval report: vendor-release-impact-issues

- Timestamp: 20261103T232007Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261103T231700Z-3b9424; started 2026-11-03T23:20:07Z, ended 2026-11-03T23:21:20Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.8 to 0.8, from 4 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.46 over 4 call(s); agent $0.29, judge $0.18, guard $0.00; last agent call $0.13

## Fixture: stamps-skip-quotes (n=1)

- Prompt: Review ExampleCLI's release notes in `vendor/` against this repository and draft the GitHub issues you would open for the changes that affect it. Every ExampleCLI version your issues mention must carry that release's publish time from `vendor/releases.json`. Write each issue to `issues/<NN>-<slug>.md`, with the issue title as the first line (`# <title>`) and the body below it. Do not open real issues.
- Harness: Claude Code `2.1.317 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 4/5 | 9.2 (9.2 to 9.2, 1 judged) | 0.1598 / 0.1598 |
| without_skill | 1 | 0 | 4/5 | 5.8 (5.8 to 5.8, 1 judged) | 0.1259 / 0.1259 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1598 / 0.1598 | 0.1259 / 0.1259 | +0.0339 | +0.0339 |
| num_turns | 6 / 6 | 4 / 4 | +2 | +2 |
| duration_ms | 30214 / 30214 | 18264 / 18264 | +11950 | +11950 |
| input_tokens | 10 / 10 | 8 / 8 | +2 | +2 |
| output_tokens | 3301 / 3301 | 2041 / 2041 | +1260 | +1260 |
| cache_creation_input_tokens | 28454 / 28454 | 23340 / 23340 | +5114 | +5114 |
| cache_read_input_tokens | 129149 / 129149 | 120771 / 120771 | +8378 | +8378 |
| tool_errors | 1 / 1 | 0 / 0 | +1 | +1 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| quotes-kept-verbatim | 1/1 | 0/1 |
| quoted-text-unstamped | 0/1 | 1/1 |
| titles-unstamped | 1/1 | 1/1 |
| prose-versions-stamped | 1/1 | 1/1 |
| seed-repo-unchanged | 1/1 | 1/1 |
