# Eval report: tool-powershell

- Timestamp: 20261107T180447Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261107T175800Z-13ef13; started 2026-11-07T18:04:47Z, ended 2026-11-07T18:06:34Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.59 to 0.59, from 6 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.46 over 6 call(s); agent $0.46, judge $0.00, guard $0.00; last agent call $0.07

## Fixture: robocopy-exit-one (n=3)

- Prompt: The nightly task marks scripts/mirror-exports.ps1 as failed: it exits with code 1 and prints nothing, yet D:\backup\export looks current. Find out why and make the task stop failing when nothing is wrong. PowerShell here is the stand-in bin/pwsh; read README.md.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 3 | 0 | 4/6 | skipped (objective-decided) | 0.0827 / 0.2482 |
| without_skill | 3 | 0 | 3.3/6 | skipped (objective-decided) | 0.0695 / 0.2084 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.0827 / 0.0734 | 0.0695 / 0.0691 | +0.0133 | +0.0044 |
| num_turns | 3.3 / 3 | 3.3 / 3 | 0 | 0 |
| duration_ms | 15893.7 / 17057 | 17374.3 / 17624 | -1480.7 | -567 |
| input_tokens | 6.7 / 6 | 6.7 / 6 | 0 | 0 |
| output_tokens | 1092.7 / 1053 | 1025.7 / 1018 | +67 | +35 |
| cache_creation_input_tokens | 15310 / 11898 | 12059.7 / 12283 | +3250.3 | -385 |
| cache_read_input_tokens | 105539 / 96954 | 109583.7 / 97421 | -4044.7 | -467 |
| tool_errors | 0 / 0 | 0 / 0 | 0 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| exit-code-read | 0/3 | 0/3 |
| no-blind-third-try | 2/3 | 0/3 |
| exit-code-mapped | 3/3 | 3/3 |
| copy-untouched | 3/3 | 3/3 |
| reply-names-cause | 1/3 | 1/3 |
| stand-in-untouched | 3/3 | 3/3 |
