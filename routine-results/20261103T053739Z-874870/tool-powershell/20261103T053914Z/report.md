# Eval report: tool-powershell

- Timestamp: 20261103T053914Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261103T053739Z-874870; started 2026-11-03T05:39:14Z, ended 2026-11-03T05:40:04Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.34 to 0.34, from 4 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.30 over 4 call(s); agent $0.17, judge $0.13, guard $0.00; last agent call $0.06

## Fixture: silent-exit-one (n=1)

- Prompt: scripts/sync-exports.ps1 exits with code 1 and prints nothing. Find out why and fix it. PowerShell here is the stand-in bin/pwsh; read README.md.
- Harness: Claude Code `2.1.317 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 4/5 | 6.0 (6.0 to 6.0, 1 judged) | 0.1039 / 0.1039 |
| without_skill | 1 | 0 | 4/5 | 6.0 (6.0 to 6.0, 1 judged) | 0.0625 / 0.0625 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1039 / 0.1039 | 0.0625 / 0.0625 | +0.0414 | +0.0414 |
| num_turns | 4 / 4 | 4 / 4 | 0 | 0 |
| duration_ms | 12102 / 12102 | 17863 / 17863 | -5761 | -5761 |
| input_tokens | 6 / 6 | 6 / 6 | 0 | 0 |
| output_tokens | 661 / 661 | 699 / 699 | -38 | -38 |
| cache_creation_input_tokens | 22180 / 22180 | 11487 / 11487 | +10693 | +10693 |
| cache_read_input_tokens | 85735 / 85735 | 95900 / 95900 | -10165 | -10165 |
| tool_errors | 0 / 0 | 0 / 0 | 0 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| error-was-surfaced | 0/1 | 0/1 |
| no-blind-third-try | 1/1 | 1/1 |
| source-path-fixed | 1/1 | 1/1 |
| dest-untouched | 1/1 | 1/1 |
| stand-in-untouched | 1/1 | 1/1 |
