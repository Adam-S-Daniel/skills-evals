# Eval report: tool-powershell

- Timestamp: 20261103T210458Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261103T205335Z-868be9; started 2026-11-03T21:04:58Z, ended 2026-11-03T21:05:50Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.71 to 0.71, from 2 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.18 over 2 call(s); agent $0.18, judge $0.00, guard $0.00; last agent call $0.06

## Fixture: silent-exit-one (n=1)

- Prompt: scripts/sync-exports.ps1 exits with code 1 and prints nothing. Find out why and fix it. PowerShell here is the stand-in bin/pwsh; read README.md.
- Harness: Claude Code `2.1.317 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 5/5 | skipped (objective-decided) | 0.1169 / 0.1169 |
| without_skill | 1 | 0 | 4/5 | skipped (objective-decided) | 0.0639 / 0.0639 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1169 / 0.1169 | 0.0639 / 0.0639 | +0.0530 | +0.0530 |
| num_turns | 6 / 6 | 4 / 4 | +2 | +2 |
| duration_ms | 34881 / 34881 | 13340 / 13340 | +21541 | +21541 |
| input_tokens | 10 / 10 | 6 / 6 | +4 | +4 |
| output_tokens | 1004 / 1004 | 792 / 792 | +212 | +212 |
| cache_creation_input_tokens | 22737 / 22737 | 11582 / 11582 | +11155 | +11155 |
| cache_read_input_tokens | 158807 / 158807 | 96088 / 96088 | +62719 | +62719 |
| tool_errors | 0 / 0 | 0 / 0 | 0 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| error-was-surfaced | 1/1 | 0/1 |
| no-blind-third-try | 1/1 | 1/1 |
| source-path-fixed | 1/1 | 1/1 |
| dest-untouched | 1/1 | 1/1 |
| stand-in-untouched | 1/1 | 1/1 |
