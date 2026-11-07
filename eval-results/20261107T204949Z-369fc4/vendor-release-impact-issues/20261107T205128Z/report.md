# Eval report: vendor-release-impact-issues

- Timestamp: 20261107T205128Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261107T204949Z-369fc4; started 2026-11-07T20:51:28Z, ended 2026-11-07T20:53:52Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.68 to 0.68, from 2 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.83 over 2 call(s); agent $0.83, judge $0.00, guard $0.00; last agent call $0.34

## Fixture: issue-hygiene (n=1)

- Prompt: Review ExampleCLI's recent release notes in `vendor/` against this repository and draft the GitHub issues you would open for the changes that affect it. Write each issue to `issues/<NN>-<slug>.md`, with the issue title as the first line (`# <title>`) and the body below it. Do not open real issues.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-opus-5-5; without_skill=claude-opus-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 7/7 | skipped (objective-decided) | 0.4974 / 0.4974 |
| without_skill | 1 | 0 | 5/7 | skipped (objective-decided) | 0.3351 / 0.3351 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.4974 / 0.4974 | 0.3351 / 0.3351 | +0.1623 | +0.1623 |
| num_turns | 9 / 9 | 5 / 5 | +4 | +4 |
| duration_ms | 85186 / 85186 | 55458 / 55458 | +29728 | +29728 |
| input_tokens | 18 / 18 | 10 / 10 | +8 | +8 |
| output_tokens | 7607 / 7607 | 4527 / 4527 | +3080 | +3080 |
| cache_creation_input_tokens | 35402 / 35402 | 26539 / 26539 | +8863 | +8863 |
| cache_read_input_tokens | 309858 / 309858 | 161142 / 161142 | +148716 | +148716 |
| tool_errors | 1 / 1 | 0 / 0 | +1 | +1 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| at-least-one-issue-drafted | 1/1 | 1/1 |
| publish-times-source-and-version-bound | 1/1 | 0/1 |
| pr-refs-fenced-not-quoted | 1/1 | 1/1 |
| no-upstream-issue-backlink | 1/1 | 1/1 |
| no-placeholder-in-title | 1/1 | 0/1 |
| seed-repo-unchanged | 1/1 | 1/1 |
| hook-matcher-surface-named | 1/1 | 1/1 |
