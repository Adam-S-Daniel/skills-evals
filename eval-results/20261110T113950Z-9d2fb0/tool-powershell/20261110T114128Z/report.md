# Eval report: tool-powershell

- Timestamp: 20261110T114128Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261110T113950Z-9d2fb0; started 2026-11-10T11:41:28Z, ended 2026-11-10T11:42:54Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.21 to 0.21, from 6 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.47 over 6 call(s); agent $0.32, judge $0.15, guard $0.00; last agent call $0.11

## Fixture: spaced-path-silent-exit (n=3)

- Prompt: scripts/pack-reports.ps1 exits with code 1 and prints nothing. Find out why and fix it. PowerShell here is the stand-in bin/pwsh; read README.md.
- Harness: Claude Code `2.1.322 (Claude Code)`; models used: without_skill=claude-opus-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| without_skill | 3 | 0 | 5/5 | 7.1 (6.3 to 8.3, 3 judged) | 0.1061 / 0.3183 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did):

| Metric (mean / median) | without_skill |
| --- | --- |
| cost_usd | 0.1061 / 0.1060 |
| num_turns | 4 / 4 |
| duration_ms | 19688.7 / 19766 |
| input_tokens | 8 / 8 |
| output_tokens | 1421.7 / 1433 |
| cache_creation_input_tokens | 9900 / 9677 |
| cache_read_input_tokens | 140734 / 140878 |
| tool_errors | 0 / 0 |

| Check (passed / scored) | without_skill |
| --- | --- |
| error-was-surfaced | 3/3 |
| no-blind-third-try | 3/3 |
| copy-uses-literalpath | 3/3 |
| defaults-untouched | 3/3 |
| stand-in-untouched | 3/3 |
