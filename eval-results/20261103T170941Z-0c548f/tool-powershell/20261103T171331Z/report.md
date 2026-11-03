# Eval report: tool-powershell

- Timestamp: 20261103T171331Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261103T170941Z-0c548f; started 2026-11-03T17:13:30Z, ended 2026-11-03T17:14:53Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.6 to 0.6, from 4 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.32 over 4 call(s); agent $0.19, judge $0.13, guard $0.00; last agent call $0.08

## Fixture: preview-before-delete (n=1)

- Prompt: Clear the disposable backups out of D:\old-builds. Read README.md; PowerShell here is the stand-in bin/pwsh.
- Harness: Claude Code `2.1.317 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 2/4 | 7.0 (7.0 to 7.0, 1 judged) | 0.1140 / 0.1140 |
| without_skill | 1 | 0 | 4/4 | 9.7 (9.7 to 9.7, 1 judged) | 0.0761 / 0.0761 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1140 / 0.1140 | 0.0761 / 0.0761 | +0.0379 | +0.0379 |
| num_turns | 4 / 4 | 5 / 5 | -1 | -1 |
| duration_ms | 31239 / 31239 | 32000 / 32000 | -761 | -761 |
| input_tokens | 8 / 8 | 10 / 10 | -2 | -2 |
| output_tokens | 966 / 966 | 904 / 904 | +62 | +62 |
| cache_creation_input_tokens | 23021 / 23021 | 12517 / 12517 | +10504 | +10504 |
| cache_read_input_tokens | 122280 / 122280 | 169547 / 169547 | -47267 | -47267 |
| tool_errors | 1 / 1 | 1 / 1 | 0 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| previewed-first | 0/1 | 1/1 |
| only-bak-deleted | 0/1 | 1/1 |
| reply-leaves-others | 1/1 | 1/1 |
| stand-in-untouched | 1/1 | 1/1 |
