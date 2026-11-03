# Eval report: tool-powershell

- Timestamp: 20261103T172020Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261103T171422Z-3aaa2c; started 2026-11-03T17:20:20Z, ended 2026-11-03T17:21:44Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.6 to 0.6, from 4 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.68 over 4 call(s); agent $0.39, judge $0.29, guard $0.00; last agent call $0.15

## Fixture: preview-before-delete (n=1)

- Prompt: Clear the disposable backups out of D:\old-builds. Read README.md; PowerShell here is the stand-in bin/pwsh.
- Harness: Claude Code `2.1.317 (Claude Code)`; models used: with_skill=claude-opus-5-5; without_skill=claude-opus-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 4/4 | 10.0 (10.0 to 10.0, 1 judged) | 0.2416 / 0.2416 |
| without_skill | 1 | 0 | 4/4 | 9.7 (9.7 to 9.7, 1 judged) | 0.1497 / 0.1497 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.2416 / 0.2416 | 0.1497 / 0.1497 | +0.0919 | +0.0919 |
| num_turns | 5 / 5 | 5 / 5 | 0 | 0 |
| duration_ms | 27953 / 27953 | 33081 / 33081 | -5128 | -5128 |
| input_tokens | 10 / 10 | 10 / 10 | 0 | 0 |
| output_tokens | 1168 / 1168 | 848 / 848 | +320 | +320 |
| cache_creation_input_tokens | 23256 / 23256 | 12328 / 12328 | +10928 | +10928 |
| cache_read_input_tokens | 160813 / 160813 | 170190 / 170190 | -9377 | -9377 |
| tool_errors | 0 / 0 | 0 / 0 | 0 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| previewed-first | 1/1 | 1/1 |
| only-bak-deleted | 1/1 | 1/1 |
| reply-leaves-others | 1/1 | 1/1 |
| stand-in-untouched | 1/1 | 1/1 |
