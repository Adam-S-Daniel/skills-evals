# Eval report: tool-powershell

- Timestamp: 20261103T190958Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261103T185116Z-7128a8; started 2026-11-03T19:09:58Z, ended 2026-11-03T19:11:04Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.67 to 0.67, from 4 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.30 over 4 call(s); agent $0.16, judge $0.13, guard $0.00; last agent call $0.06

## Fixture: silent-exit-one (n=1)

- Prompt: scripts/sync-exports.ps1 exits with code 1 and prints nothing. Find out why and fix it. PowerShell here is the stand-in bin/pwsh; read README.md.
- Harness: Claude Code `2.1.317 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 4/5 | 5.5 (5.5 to 5.5, 1 judged) | 0.1028 / 0.1028 |
| without_skill | 1 | 0 | 4/5 | 6.7 (6.7 to 6.7, 1 judged) | 0.0617 / 0.0617 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1028 / 0.1028 | 0.0617 / 0.0617 | +0.0411 | +0.0411 |
| num_turns | 3 / 3 | 4 / 4 | -1 | -1 |
| duration_ms | 25381 / 25381 | 15264 / 15264 | +10117 | +10117 |
| input_tokens | 6 / 6 | 6 / 6 | 0 | 0 |
| output_tokens | 620 / 620 | 656 / 656 | -36 | -36 |
| cache_creation_input_tokens | 21998 / 21998 | 11389 / 11389 | +10609 | +10609 |
| cache_read_input_tokens | 85647 / 85647 | 95873 / 95873 | -10226 | -10226 |
| tool_errors | 0 / 0 | 0 / 0 | 0 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| error-was-surfaced | 0/1 | 0/1 |
| no-blind-third-try | 1/1 | 1/1 |
| source-path-fixed | 1/1 | 1/1 |
| dest-untouched | 1/1 | 1/1 |
| stand-in-untouched | 1/1 | 1/1 |
