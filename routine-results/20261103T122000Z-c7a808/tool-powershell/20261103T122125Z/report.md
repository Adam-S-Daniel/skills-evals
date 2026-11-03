# Eval report: tool-powershell

- Timestamp: 20261103T122125Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261103T122000Z-c7a808; started 2026-11-03T12:21:25Z, ended 2026-11-03T12:22:55Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.39 to 0.39, from 4 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $1.49 over 4 call(s); agent $0.54, judge $0.95, guard $0.00; last agent call $0.16

## Fixture: silent-exit-one (n=1)

- Prompt: scripts/sync-exports.ps1 exits with code 1 and prints nothing. Find out why and fix it. PowerShell here is the stand-in bin/pwsh; read README.md.
- Harness: Claude Code `2.1.317 (Claude Code)`; models used: with_skill=claude-opus-5-5; without_skill=claude-opus-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 5/5 | 9.0 (9.0 to 9.0, 1 judged) | 0.3850 / 0.3850 |
| without_skill | 1 | 0 | 5/5 | 9.7 (9.7 to 9.7, 1 judged) | 0.1577 / 0.1577 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.3850 / 0.3850 | 0.1577 / 0.1577 | +0.2273 | +0.2273 |
| num_turns | 8 / 8 | 4 / 4 | +4 | +4 |
| duration_ms | 30094 / 30094 | 28244 / 28244 | +1850 | +1850 |
| input_tokens | 12 / 12 | 8 / 8 | +4 | +4 |
| output_tokens | 1763 / 1763 | 1382 / 1382 | +381 | +381 |
| cache_creation_input_tokens | 39921 / 39921 | 12900 / 12900 | +27021 | +27021 |
| cache_read_input_tokens | 151452 / 151452 | 133932 / 133932 | +17520 | +17520 |
| tool_errors | 0 / 0 | 0 / 0 | 0 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| error-was-surfaced | 1/1 | 1/1 |
| no-blind-third-try | 1/1 | 1/1 |
| source-path-fixed | 1/1 | 1/1 |
| dest-untouched | 1/1 | 1/1 |
| stand-in-untouched | 1/1 | 1/1 |
