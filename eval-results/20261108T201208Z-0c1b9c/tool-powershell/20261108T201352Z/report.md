# Eval report: tool-powershell

- Timestamp: 20261108T201352Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261108T201208Z-0c1b9c; started 2026-11-08T20:13:52Z, ended 2026-11-08T20:14:44Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.87 to 0.87, from 4 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.21 over 4 call(s); agent $0.16, judge $0.05, guard $0.00; last agent call $0.05

## Fixture: spaced-path-silent-exit (n=1)

- Prompt: scripts/pack-reports.ps1 exits with code 1 and prints nothing. Find out why and fix it. PowerShell here is the stand-in bin/pwsh; read README.md.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 5/5 | 6.3 (6.3 to 6.3, 1 judged) | 0.1123 / 0.1123 |
| without_skill | 1 | 0 | 5/5 | 7.7 (7.7 to 7.7, 1 judged) | 0.0509 / 0.0509 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1123 / 0.1123 | 0.0509 / 0.0509 | +0.0614 | +0.0614 |
| num_turns | 4 / 4 | 4 / 4 | 0 | 0 |
| duration_ms | 17035 / 17035 | 17034 / 17034 | +1 | +1 |
| input_tokens | 8 / 8 | 8 / 8 | 0 | 0 |
| output_tokens | 940 / 940 | 943 / 943 | -3 | -3 |
| cache_creation_input_tokens | 36809 / 36809 | 11241 / 11241 | +25568 | +25568 |
| cache_read_input_tokens | 108272 / 108272 | 133121 / 133121 | -24849 | -24849 |
| tool_errors | 0 / 0 | 0 / 0 | 0 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| error-was-surfaced | 1/1 | 1/1 |
| no-blind-third-try | 1/1 | 1/1 |
| copy-uses-literalpath | 1/1 | 1/1 |
| defaults-untouched | 1/1 | 1/1 |
| stand-in-untouched | 1/1 | 1/1 |
