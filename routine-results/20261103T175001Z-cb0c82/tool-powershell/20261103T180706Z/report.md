# Eval report: tool-powershell

- Timestamp: 20261103T180706Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261103T175001Z-cb0c82; started 2026-11-03T18:07:06Z, ended 2026-11-03T18:08:06Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.63 to 0.63, from 4 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.30 over 4 call(s); agent $0.17, judge $0.13, guard $0.00; last agent call $0.06

## Fixture: silent-exit-one (n=1)

- Prompt: scripts/sync-exports.ps1 exits with code 1 and prints nothing. Find out why and fix it. PowerShell here is the stand-in bin/pwsh; read README.md.
- Harness: Claude Code `2.1.317 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 4/5 | 5.5 (5.5 to 5.5, 1 judged) | 0.1046 / 0.1046 |
| without_skill | 1 | 0 | 4/5 | 7.0 (7.0 to 7.0, 1 judged) | 0.0626 / 0.0626 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1046 / 0.1046 | 0.0626 / 0.0626 | +0.0420 | +0.0420 |
| num_turns | 4 / 4 | 4 / 4 | 0 | 0 |
| duration_ms | 18217 / 18217 | 21001 / 21001 | -2784 | -2784 |
| input_tokens | 6 / 6 | 6 / 6 | 0 | 0 |
| output_tokens | 756 / 756 | 752 / 752 | +4 | +4 |
| cache_creation_input_tokens | 22111 / 22111 | 11371 / 11371 | +10740 | +10740 |
| cache_read_input_tokens | 85499 / 85499 | 95624 / 95624 | -10125 | -10125 |
| tool_errors | 0 / 0 | 0 / 0 | 0 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| error-was-surfaced | 0/1 | 0/1 |
| no-blind-third-try | 1/1 | 1/1 |
| source-path-fixed | 1/1 | 1/1 |
| dest-untouched | 1/1 | 1/1 |
| stand-in-untouched | 1/1 | 1/1 |
