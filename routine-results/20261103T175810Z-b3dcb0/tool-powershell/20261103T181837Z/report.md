# Eval report: tool-powershell

- Timestamp: 20261103T181837Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261103T175810Z-b3dcb0; started 2026-11-03T18:18:37Z, ended 2026-11-03T18:20:02Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.64 to 0.64, from 4 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.68 over 4 call(s); agent $0.39, judge $0.29, guard $0.00; last agent call $0.15

## Fixture: preview-before-delete (n=1)

- Prompt: Clear the disposable backups out of D:\old-builds. Read README.md; PowerShell here is the stand-in bin/pwsh.
- Harness: Claude Code `2.1.317 (Claude Code)`; models used: with_skill=claude-opus-5-5; without_skill=claude-opus-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 4/4 | 9.7 (9.7 to 9.7, 1 judged) | 0.2412 / 0.2412 |
| without_skill | 1 | 0 | 4/4 | 9.3 (9.3 to 9.3, 1 judged) | 0.1527 / 0.1527 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.2412 / 0.2412 | 0.1527 / 0.1527 | +0.0885 | +0.0885 |
| num_turns | 5 / 5 | 5 / 5 | 0 | 0 |
| duration_ms | 31503 / 31503 | 30574 / 30574 | +929 | +929 |
| input_tokens | 10 / 10 | 10 / 10 | 0 | 0 |
| output_tokens | 1102 / 1102 | 956 / 956 | +146 | +146 |
| cache_creation_input_tokens | 23376 / 23376 | 12434 / 12434 | +10942 | +10942 |
| cache_read_input_tokens | 160778 / 160778 | 170452 / 170452 | -9674 | -9674 |
| tool_errors | 1 / 1 | 0 / 0 | +1 | +1 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| previewed-first | 1/1 | 1/1 |
| only-bak-deleted | 1/1 | 1/1 |
| reply-leaves-others | 1/1 | 1/1 |
| stand-in-untouched | 1/1 | 1/1 |
