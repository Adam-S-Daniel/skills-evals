# Eval report: tool-powershell

- Timestamp: 20261103T143244Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261103T143035Z-a74376; started 2026-11-03T14:32:44Z, ended 2026-11-03T14:33:50Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.48 to 0.48, from 4 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.32 over 4 call(s); agent $0.20, judge $0.13, guard $0.00; last agent call $0.08

## Fixture: preview-before-delete (n=1)

- Prompt: Clear the disposable backups out of D:\old-builds. Read README.md; PowerShell here is the stand-in bin/pwsh.
- Harness: Claude Code `2.1.317 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 4/4 | 8.7 (8.7 to 8.7, 1 judged) | 0.1204 / 0.1204 |
| without_skill | 1 | 0 | 4/4 | 9.3 (9.3 to 9.3, 1 judged) | 0.0782 / 0.0782 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1204 / 0.1204 | 0.0782 / 0.0782 | +0.0422 | +0.0422 |
| num_turns | 6 / 6 | 5 / 5 | +1 | +1 |
| duration_ms | 25090 / 25090 | 22910 / 22910 | +2180 | +2180 |
| input_tokens | 10 / 10 | 10 / 10 | 0 | 0 |
| output_tokens | 1031 / 1031 | 1061 / 1061 | -30 | -30 |
| cache_creation_input_tokens | 23499 / 23499 | 12658 / 12658 | +10841 | +10841 |
| cache_read_input_tokens | 160675 / 160675 | 169810 / 169810 | -9135 | -9135 |
| tool_errors | 1 / 1 | 1 / 1 | 0 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| previewed-first | 1/1 | 1/1 |
| only-bak-deleted | 1/1 | 1/1 |
| reply-leaves-others | 1/1 | 1/1 |
| stand-in-untouched | 1/1 | 1/1 |
