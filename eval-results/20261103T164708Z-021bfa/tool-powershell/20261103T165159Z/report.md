# Eval report: tool-powershell

- Timestamp: 20261103T165159Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261103T164708Z-021bfa; started 2026-11-03T16:51:59Z, ended 2026-11-03T16:53:12Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.59 to 0.59, from 4 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.71 over 4 call(s); agent $0.41, judge $0.30, guard $0.00; last agent call $0.15

## Fixture: silent-exit-one (n=1)

- Prompt: scripts/sync-exports.ps1 exits with code 1 and prints nothing. Find out why and fix it. PowerShell here is the stand-in bin/pwsh; read README.md.
- Harness: Claude Code `2.1.317 (Claude Code)`; models used: with_skill=claude-opus-5-5; without_skill=claude-opus-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 5/5 | 9.3 (9.3 to 9.3, 1 judged) | 0.2613 / 0.2613 |
| without_skill | 1 | 0 | 5/5 | 9.0 (9.0 to 9.0, 1 judged) | 0.1527 / 0.1527 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.2613 / 0.2613 | 0.1527 / 0.1527 | +0.1085 | +0.1085 |
| num_turns | 7 / 7 | 4 / 4 | +3 | +3 |
| duration_ms | 32742 / 32742 | 25257 / 25257 | +7485 | +7485 |
| input_tokens | 12 / 12 | 8 / 8 | +4 | +4 |
| output_tokens | 1374 / 1374 | 1259 / 1259 | +115 | +115 |
| cache_creation_input_tokens | 25090 / 25090 | 12590 / 12590 | +12500 | +12500 |
| cache_read_input_tokens | 165187 / 165187 | 134080 / 134080 | +31107 | +31107 |
| tool_errors | 0 / 0 | 0 / 0 | 0 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| error-was-surfaced | 1/1 | 1/1 |
| no-blind-third-try | 1/1 | 1/1 |
| source-path-fixed | 1/1 | 1/1 |
| dest-untouched | 1/1 | 1/1 |
| stand-in-untouched | 1/1 | 1/1 |
