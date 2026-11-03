# Eval report: tool-powershell

- Timestamp: 20261103T164743Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261103T163135Z-005452; started 2026-11-03T16:47:43Z, ended 2026-11-03T16:48:42Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.59 to 0.59, from 4 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.30 over 4 call(s); agent $0.17, judge $0.13, guard $0.00; last agent call $0.07

## Fixture: silent-exit-one (n=1)

- Prompt: scripts/sync-exports.ps1 exits with code 1 and prints nothing. Find out why and fix it. PowerShell here is the stand-in bin/pwsh; read README.md.
- Harness: Claude Code `2.1.317 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 4/5 | 7.3 (7.3 to 7.3, 1 judged) | 0.1047 / 0.1047 |
| without_skill | 1 | 0 | 4/5 | 6.7 (6.7 to 6.7, 1 judged) | 0.0668 / 0.0668 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1047 / 0.1047 | 0.0668 / 0.0668 | +0.0380 | +0.0380 |
| num_turns | 4 / 4 | 4 / 4 | 0 | 0 |
| duration_ms | 23766 / 23766 | 16519 / 16519 | +7247 | +7247 |
| input_tokens | 6 / 6 | 6 / 6 | 0 | 0 |
| output_tokens | 733 / 733 | 787 / 787 | -54 | -54 |
| cache_creation_input_tokens | 22202 / 22202 | 12301 / 12301 | +9901 | +9901 |
| cache_read_input_tokens | 85655 / 85655 | 96719 / 96719 | -11064 | -11064 |
| tool_errors | 0 / 0 | 0 / 0 | 0 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| error-was-surfaced | 0/1 | 0/1 |
| no-blind-third-try | 1/1 | 1/1 |
| source-path-fixed | 1/1 | 1/1 |
| dest-untouched | 1/1 | 1/1 |
| stand-in-untouched | 1/1 | 1/1 |
