# Eval report: tool-powershell

- Timestamp: 20261107T220621Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261107T220444Z-e47c5f; started 2026-11-07T22:06:21Z, ended 2026-11-07T22:06:57Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.69 to 0.69, from 2 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.18 over 2 call(s); agent $0.18, judge $0.00, guard $0.00; last agent call $0.07

## Fixture: robocopy-exit-one (n=1)

- Prompt: The nightly task marks scripts/mirror-exports.ps1 as failed: it exits with code 1 and prints nothing, yet D:\backup\export looks current. Find out why and make the task stop failing when nothing is wrong. PowerShell here is the stand-in bin/pwsh; read README.md.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 6/6 | skipped (objective-decided) | 0.1121 / 0.1121 |
| without_skill | 1 | 0 | 3/6 | skipped (objective-decided) | 0.0658 / 0.0658 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1121 / 0.1121 | 0.0658 / 0.0658 | +0.0463 | +0.0463 |
| num_turns | 5 / 5 | 3 / 3 | +2 | +2 |
| duration_ms | 18514 / 18514 | 14990 / 14990 | +3524 | +3524 |
| input_tokens | 6 / 6 | 6 / 6 | 0 | 0 |
| output_tokens | 1184 / 1184 | 954 / 954 | +230 | +230 |
| cache_creation_input_tokens | 22892 / 22892 | 11638 / 11638 | +11254 | +11254 |
| cache_read_input_tokens | 86397 / 86397 | 96948 / 96948 | -10551 | -10551 |
| tool_errors | 0 / 0 | 0 / 0 | 0 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| exit-code-read | 1/1 | 0/1 |
| no-blind-third-try | 1/1 | 0/1 |
| exit-code-mapped | 1/1 | 1/1 |
| copy-untouched | 1/1 | 1/1 |
| reply-names-cause | 1/1 | 0/1 |
| stand-in-untouched | 1/1 | 1/1 |
