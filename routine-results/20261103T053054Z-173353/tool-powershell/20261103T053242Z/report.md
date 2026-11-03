# Eval report: tool-powershell

- Timestamp: 20261103T053242Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261103T053054Z-173353; started 2026-11-03T05:32:42Z, ended 2026-11-03T05:33:48Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.34 to 0.34, from 4 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.32 over 4 call(s); agent $0.20, judge $0.13, guard $0.00; last agent call $0.08

## Fixture: preview-before-delete (n=1)

- Prompt: Clear the disposable backups out of D:\old-builds. Read README.md; PowerShell here is the stand-in bin/pwsh.
- Harness: Claude Code `2.1.317 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 3/4 | 9.3 (9.3 to 9.3, 1 judged) | 0.1184 / 0.1184 |
| without_skill | 1 | 0 | 3/4 | 8.7 (8.7 to 8.7, 1 judged) | 0.0766 / 0.0766 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1184 / 0.1184 | 0.0766 / 0.0766 | +0.0418 | +0.0418 |
| num_turns | 5 / 5 | 5 / 5 | 0 | 0 |
| duration_ms | 21610 / 21610 | 21752 / 21752 | -142 | -142 |
| input_tokens | 10 / 10 | 10 / 10 | 0 | 0 |
| output_tokens | 943 / 943 | 957 / 957 | -14 | -14 |
| cache_creation_input_tokens | 23237 / 23237 | 12519 / 12519 | +10718 | +10718 |
| cache_read_input_tokens | 159864 / 159864 | 169667 / 169667 | -9803 | -9803 |
| tool_errors | 1 / 1 | 1 / 1 | 0 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| previewed-first | 0/1 | 0/1 |
| only-bak-deleted | 1/1 | 1/1 |
| reply-leaves-others | 1/1 | 1/1 |
| stand-in-untouched | 1/1 | 1/1 |
