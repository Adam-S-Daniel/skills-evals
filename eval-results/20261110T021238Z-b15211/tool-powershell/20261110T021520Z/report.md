# Eval report: tool-powershell

- Timestamp: 20261110T021520Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261110T021238Z-b15211; started 2026-11-10T02:15:20Z, ended 2026-11-10T02:16:42Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.15 to 0.15, from 6 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.28 over 6 call(s); agent $0.21, judge $0.07, guard $0.00; last agent call $0.05

## Fixture: spaced-path-silent-exit (n=3)

- Prompt: scripts/pack-reports.ps1 exits with code 1 and prints nothing. Find out why and fix it. PowerShell here is the stand-in bin/pwsh; read README.md.
- Harness: Claude Code `2.1.321 (Claude Code)`; models used: without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| without_skill | 3 | 0 | 5/5 | 7.0 (5.3 to 9.0, 3 judged) | 0.0701 / 0.2102 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did):

| Metric (mean / median) | without_skill |
| --- | --- |
| cost_usd | 0.0701 / 0.0472 |
| num_turns | 4 / 4 |
| duration_ms | 18986.7 / 18343 |
| input_tokens | 8 / 8 |
| output_tokens | 1021.7 / 1016 |
| cache_creation_input_tokens | 18699 / 9111 |
| cache_read_input_tokens | 130731.3 / 140332 |
| tool_errors | 0 / 0 |

| Check (passed / scored) | without_skill |
| --- | --- |
| error-was-surfaced | 3/3 |
| no-blind-third-try | 3/3 |
| copy-uses-literalpath | 3/3 |
| defaults-untouched | 3/3 |
| stand-in-untouched | 3/3 |
