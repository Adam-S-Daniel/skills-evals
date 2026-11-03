# Eval report: tool-powershell

- Timestamp: 20261103T202104Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261103T200456Z-cf3279; started 2026-11-03T20:21:04Z, ended 2026-11-03T20:22:10Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.69 to 0.69, from 2 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.43 over 2 call(s); agent $0.43, judge $0.00, guard $0.00; last agent call $0.17

## Fixture: silent-exit-one (n=1)

- Prompt: scripts/sync-exports.ps1 exits with code 1 and prints nothing. Find out why and fix it. PowerShell here is the stand-in bin/pwsh; read README.md.
- Harness: Claude Code `2.1.317 (Claude Code)`; models used: with_skill=claude-opus-5-5; without_skill=claude-opus-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 5/5 | skipped (objective-decided) | 0.2629 / 0.2629 |
| without_skill | 1 | 0 | 3/5 | skipped (objective-decided) | 0.1686 / 0.1686 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.2629 / 0.2629 | 0.1686 / 0.1686 | +0.0942 | +0.0942 |
| num_turns | 7 / 7 | 5 / 5 | +2 | +2 |
| duration_ms | 27863 / 27863 | 31676 / 31676 | -3813 | -3813 |
| input_tokens | 12 / 12 | 10 / 10 | +2 | +2 |
| output_tokens | 1411 / 1411 | 1501 / 1501 | -90 | -90 |
| cache_creation_input_tokens | 25192 / 25192 | 13058 / 13058 | +12134 | +12134 |
| cache_read_input_tokens | 165252 / 165252 | 170428 / 170428 | -5176 | -5176 |
| tool_errors | 0 / 0 | 0 / 0 | 0 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| error-was-surfaced | 1/1 | 0/1 |
| no-blind-third-try | 1/1 | 0/1 |
| source-path-fixed | 1/1 | 1/1 |
| dest-untouched | 1/1 | 1/1 |
| stand-in-untouched | 1/1 | 1/1 |
