# Eval report: tool-powershell

- Timestamp: 20261107T144418Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261107T144242Z-d78fc6; started 2026-11-07T14:44:18Z, ended 2026-11-07T14:48:40Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.46 to 0.46, from 12 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $1.81 over 12 call(s); agent $1.28, judge $0.53, guard $0.00; last agent call $0.22

## Fixture: robocopy-exit-one (n=3)

- Prompt: The nightly task marks scripts/mirror-exports.ps1 as failed: it exits with code 1 and prints nothing, yet D:\backup\export looks current. Find out why and make the task stop failing when nothing is wrong. PowerShell here is the stand-in bin/pwsh; read README.md.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-opus-5-5; without_skill=claude-opus-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 3 | 0 | 4.3/6 | 8.9 (8.7 to 9.0, 3 judged) | 0.2371 / 0.7114 |
| without_skill | 3 | 0 | 4.3/6 | 9.2 (9.0 to 9.3, 3 judged) | 0.1883 / 0.5648 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.2371 / 0.2023 | 0.1883 / 0.1784 | +0.0489 | +0.0239 |
| num_turns | 7 / 7 | 6 / 5 | +1 | +2 |
| duration_ms | 30870 / 29299 | 30639.3 / 25362 | +230.7 | +3937 |
| input_tokens | 12 / 10 | 10 / 10 | +2 | 0 |
| output_tokens | 2514.7 / 2523 | 2210.3 / 1884 | +304.3 | +639 |
| cache_creation_input_tokens | 18413 / 14614 | 13690.3 / 13373 | +4722.7 | +1241 |
| cache_read_input_tokens | 197395.7 / 174686 | 172500.3 / 171223 | +24895.3 | +3463 |
| tool_errors | 0 / 0 | 0 / 0 | 0 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| exit-code-read | 2/3 | 2/3 |
| no-blind-third-try | 2/3 | 2/3 |
| exit-code-mapped | 3/3 | 3/3 |
| copy-untouched | 3/3 | 3/3 |
| reply-names-cause | 0/3 | 0/3 |
| stand-in-untouched | 3/3 | 3/3 |
