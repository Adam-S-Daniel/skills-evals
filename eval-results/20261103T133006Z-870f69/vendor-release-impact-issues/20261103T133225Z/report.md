# Eval report: vendor-release-impact-issues

- Timestamp: 20261103T133225Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261103T133006Z-870f69; started 2026-11-03T13:32:25Z, ended 2026-11-03T13:33:46Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.44 to 0.44, from 2 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.31 over 2 call(s); agent $0.31, judge $0.00, guard $0.00; last agent call $0.13

## Fixture: stamps-skip-quotes (n=1)

- Prompt: Review ExampleCLI's release notes in `vendor/` against this repository and draft the GitHub issues you would open for the changes that affect it. Every ExampleCLI version your issues mention must carry that release's publish time from `vendor/releases.json`. Write each issue to `issues/<NN>-<slug>.md`, with the issue title as the first line (`# <title>`) and the body below it. Do not open real issues.
- Harness: Claude Code `2.1.317 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 5/5 | skipped (objective-decided) | 0.1795 / 0.1795 |
| without_skill | 1 | 0 | 4/5 | skipped (objective-decided) | 0.1272 / 0.1272 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1795 / 0.1795 | 0.1272 / 0.1272 | +0.0523 | +0.0523 |
| num_turns | 6 / 6 | 4 / 4 | +2 | +2 |
| duration_ms | 55279 / 55279 | 19752 / 19752 | +35527 | +35527 |
| input_tokens | 10 / 10 | 8 / 8 | +2 | +2 |
| output_tokens | 4264 / 4264 | 2117 / 2117 | +2147 | +2147 |
| cache_creation_input_tokens | 30979 / 30979 | 23484 / 23484 | +7495 | +7495 |
| cache_read_input_tokens | 129269 / 129269 | 120943 / 120943 | +8326 | +8326 |
| tool_errors | 0 / 0 | 0 / 0 | 0 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| quotes-kept-verbatim | 1/1 | 0/1 |
| quoted-text-unstamped | 1/1 | 1/1 |
| titles-unstamped | 1/1 | 1/1 |
| prose-versions-stamped | 1/1 | 1/1 |
| seed-repo-unchanged | 1/1 | 1/1 |
