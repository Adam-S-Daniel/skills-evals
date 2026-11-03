# Eval report: tool-powershell

- Timestamp: 20261103T181444Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261103T175938Z-c6f09c; started 2026-11-03T18:14:44Z, ended 2026-11-03T18:16:02Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.64 to 0.64, from 4 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.76 over 4 call(s); agent $0.43, judge $0.33, guard $0.00; last agent call $0.16

## Fixture: silent-exit-one (n=1)

- Prompt: scripts/sync-exports.ps1 exits with code 1 and prints nothing. Find out why and fix it. PowerShell here is the stand-in bin/pwsh; read README.md.
- Harness: Claude Code `2.1.317 (Claude Code)`; models used: with_skill=claude-opus-5-5; without_skill=claude-opus-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 5/5 | 9.3 (9.3 to 9.3, 1 judged) | 0.2656 / 0.2656 |
| without_skill | 1 | 0 | 5/5 | 9.0 (9.0 to 9.0, 1 judged) | 0.1622 / 0.1622 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.2656 / 0.2656 | 0.1622 / 0.1622 | +0.1035 | +0.1035 |
| num_turns | 8 / 8 | 5 / 5 | +3 | +3 |
| duration_ms | 27118 / 27118 | 26345 / 26345 | +773 | +773 |
| input_tokens | 12 / 12 | 10 / 10 | +2 | +2 |
| output_tokens | 1514 / 1514 | 1241 / 1241 | +273 | +273 |
| cache_creation_input_tokens | 25282 / 25282 | 12890 / 12890 | +12392 | +12392 |
| cache_read_input_tokens | 165212 / 165212 | 170903 / 170903 | -5691 | -5691 |
| tool_errors | 0 / 0 | 0 / 0 | 0 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| error-was-surfaced | 1/1 | 1/1 |
| no-blind-third-try | 1/1 | 1/1 |
| source-path-fixed | 1/1 | 1/1 |
| dest-untouched | 1/1 | 1/1 |
| stand-in-untouched | 1/1 | 1/1 |
