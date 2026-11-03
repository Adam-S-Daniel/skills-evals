# Eval report: tool-powershell

- Timestamp: 20261103T193917Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261103T192351Z-132281; started 2026-11-03T19:39:17Z, ended 2026-11-03T19:40:50Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.68 to 0.68, from 4 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.37 over 4 call(s); agent $0.25, judge $0.13, guard $0.00; last agent call $0.07

## Fixture: preview-before-delete (n=1)

- Prompt: Clear the disposable backups out of D:\old-builds. Read README.md; PowerShell here is the stand-in bin/pwsh.
- Harness: Claude Code `2.1.317 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 4/4 | 8.0 (8.0 to 8.0, 1 judged) | 0.1776 / 0.1776 |
| without_skill | 1 | 0 | 4/4 | 8.3 (8.3 to 8.3, 1 judged) | 0.0677 / 0.0677 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1776 / 0.1776 | 0.0677 / 0.0677 | +0.1099 | +0.1099 |
| num_turns | 5 / 5 | 5 / 5 | 0 | 0 |
| duration_ms | 35013 / 35013 | 38626 / 38626 | -3613 | -3613 |
| input_tokens | 10 / 10 | 10 / 10 | 0 | 0 |
| output_tokens | 816 / 816 | 911 / 911 | -95 | -95 |
| cache_creation_input_tokens | 38590 / 38590 | 10185 / 10185 | +28405 | +28405 |
| cache_read_input_tokens | 150626 / 150626 | 178741 / 178741 | -28115 | -28115 |
| tool_errors | 0 / 0 | 1 / 1 | -1 | -1 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| previewed-first | 1/1 | 1/1 |
| only-bak-deleted | 1/1 | 1/1 |
| reply-leaves-others | 1/1 | 1/1 |
| stand-in-untouched | 1/1 | 1/1 |
