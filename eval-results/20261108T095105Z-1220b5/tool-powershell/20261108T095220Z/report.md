# Eval report: tool-powershell

- Timestamp: 20261108T095220Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261108T095105Z-1220b5; started 2026-11-08T09:52:20Z, ended 2026-11-08T09:53:41Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.75 to 0.75, from 6 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.38 over 6 call(s); agent $0.28, judge $0.09, guard $0.00; last agent call $0.06

## Fixture: robocopy-exit-one (n=3)

- Prompt: The nightly task marks scripts/mirror-exports.ps1 as failed: it exits with code 1 and prints nothing, yet D:\backup\export looks current. Find out why and make the task stop failing when nothing is wrong. PowerShell here is the stand-in bin/pwsh; read README.md.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| without_skill | 3 | 0 | 4.7/6 | 6.8 (6.7 to 7.0, 3 judged) | 0.0948 / 0.2845 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did):

| Metric (mean / median) | without_skill |
| --- | --- |
| cost_usd | 0.0948 / 0.0570 |
| num_turns | 3.3 / 3 |
| duration_ms | 17319 / 16435 |
| input_tokens | 6.7 / 6 |
| output_tokens | 925.7 / 928 |
| cache_creation_input_tokens | 18759.7 / 9295 |
| cache_read_input_tokens | 105195 / 102462 |
| tool_errors | 0 / 0 |

| Check (passed / scored) | without_skill |
| --- | --- |
| exit-code-read | 0/3 |
| no-blind-third-try | 3/3 |
| exit-code-mapped | 3/3 |
| copy-untouched | 3/3 |
| reply-names-cause | 2/3 |
| stand-in-untouched | 3/3 |
