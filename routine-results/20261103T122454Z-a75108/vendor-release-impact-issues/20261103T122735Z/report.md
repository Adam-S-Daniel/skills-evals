# Eval report: vendor-release-impact-issues

- Timestamp: 20261103T122735Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261103T122454Z-a75108; started 2026-11-03T12:27:35Z, ended 2026-11-03T12:29:56Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.4 to 0.4, from 2 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.82 over 2 call(s); agent $0.82, judge $0.00, guard $0.00; last agent call $0.35

## Fixture: issue-hygiene (n=1)

- Prompt: Review ExampleCLI's recent release notes in `vendor/` against this repository and draft the GitHub issues you would open for the changes that affect it. Write each issue to `issues/<NN>-<slug>.md`, with the issue title as the first line (`# <title>`) and the body below it. Do not open real issues.
- Harness: Claude Code `2.1.317 (Claude Code)`; models used: with_skill=claude-opus-5-5; without_skill=claude-opus-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 7/7 | skipped (objective-decided) | 0.4744 / 0.4744 |
| without_skill | 1 | 0 | 4/7 | skipped (objective-decided) | 0.3486 / 0.3486 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.4744 / 0.4744 | 0.3486 / 0.3486 | +0.1258 | +0.1258 |
| num_turns | 8 / 8 | 4 / 4 | +4 | +4 |
| duration_ms | 76132 / 76132 | 58434 / 58434 | +17698 | +17698 |
| input_tokens | 14 / 14 | 8 / 8 | +6 | +6 |
| output_tokens | 7246 / 7246 | 5168 / 5168 | +2078 | +2078 |
| cache_creation_input_tokens | 35603 / 35603 | 27587 / 27587 | +8016 | +8016 |
| cache_read_input_tokens | 223023 / 223023 | 122486 / 122486 | +100537 | +100537 |
| tool_errors | 1 / 1 | 1 / 1 | 0 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| at-least-one-issue-drafted | 1/1 | 1/1 |
| publish-times-source-and-version-bound | 1/1 | 0/1 |
| pr-refs-fenced-not-quoted | 1/1 | 1/1 |
| no-upstream-issue-backlink | 1/1 | 0/1 |
| no-placeholder-in-title | 1/1 | 0/1 |
| seed-repo-unchanged | 1/1 | 1/1 |
| hook-matcher-surface-named | 1/1 | 1/1 |
