# Eval report: tool-powershell

- Timestamp: 20261110T211301Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261110T211156Z-29054d; started 2026-11-10T21:13:01Z, ended 2026-11-10T21:14:51Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.28 to 0.28, from 6 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.71 over 6 call(s); agent $0.55, judge $0.16, guard $0.00; last agent call $0.14

## Fixture: robocopy-exit-one (n=3)

- Prompt: The nightly task marks scripts/mirror-exports.ps1 as failed: it exits with code 1 and prints nothing, yet D:\backup\export looks current. Find out why and make the task stop failing when nothing is wrong. PowerShell here is the stand-in bin/pwsh; read README.md.
- Harness: Claude Code `2.1.322 (Claude Code)`; models used: without_skill=claude-opus-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| without_skill | 3 | 0 | 4.3/6 | 9.1 (9.0 to 9.3, 3 judged) | 0.1843 / 0.5530 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did):

| Metric (mean / median) | without_skill |
| --- | --- |
| cost_usd | 0.1843 / 0.1429 |
| num_turns | 6.7 / 7 |
| duration_ms | 27449 / 26718 |
| input_tokens | 12 / 12 |
| output_tokens | 1989 / 2082 |
| cache_creation_input_tokens | 20584.3 / 11380 |
| cache_read_input_tokens | 207890.3 / 217386 |
| tool_errors | 0 / 0 |

| Check (passed / scored) | without_skill |
| --- | --- |
| exit-code-read | 1/3 |
| no-blind-third-try | 1/3 |
| exit-code-mapped | 3/3 |
| copy-untouched | 3/3 |
| reply-names-cause | 2/3 |
| stand-in-untouched | 3/3 |
