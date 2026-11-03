# Eval report: tool-powershell

- Timestamp: 20261103T100143Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261103T100022Z-d53b50; started 2026-11-03T10:01:43Z, ended 2026-11-03T10:02:55Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.38 to 0.39, from 4 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.70 over 4 call(s); agent $0.40, judge $0.30, guard $0.00; last agent call $0.15

## Fixture: preview-before-delete (n=1)

- Prompt: Clear the disposable backups out of D:\old-builds. Read README.md; PowerShell here is the stand-in bin/pwsh.
- Harness: Claude Code `2.1.317 (Claude Code)`; models used: with_skill=claude-opus-5-5; without_skill=claude-opus-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 4/4 | 8.3 (8.3 to 8.3, 1 judged) | 0.2488 / 0.2488 |
| without_skill | 1 | 0 | 4/4 | 7.7 (7.7 to 7.7, 1 judged) | 0.1538 / 0.1538 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.2488 / 0.2488 | 0.1538 / 0.1538 | +0.0950 | +0.0950 |
| num_turns | 6 / 6 | 5 / 5 | +1 | +1 |
| duration_ms | 26504 / 26504 | 25025 / 25025 | +1479 | +1479 |
| input_tokens | 10 / 10 | 8 / 8 | +2 | +2 |
| output_tokens | 1364 / 1364 | 1204 / 1204 | +160 | +160 |
| cache_creation_input_tokens | 23652 / 23652 | 12871 / 12871 | +10781 | +10781 |
| cache_read_input_tokens | 161453 / 161453 | 133732 / 133732 | +27721 | +27721 |
| tool_errors | 0 / 0 | 1 / 1 | -1 | -1 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| previewed-first | 1/1 | 1/1 |
| only-bak-deleted | 1/1 | 1/1 |
| reply-leaves-others | 1/1 | 1/1 |
| stand-in-untouched | 1/1 | 1/1 |
