# Eval report: tool-powershell

- Timestamp: 20261107T144842Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261107T144242Z-d78fc6; started 2026-11-07T14:48:42Z, ended 2026-11-07T14:51:15Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.46 to 0.46, from 12 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.64 over 12 call(s); agent $0.44, judge $0.19, guard $0.00; last agent call $0.07

## Fixture: robocopy-exit-one (n=3)

- Prompt: The nightly task marks scripts/mirror-exports.ps1 as failed: it exits with code 1 and prints nothing, yet D:\backup\export looks current. Find out why and make the task stop failing when nothing is wrong. PowerShell here is the stand-in bin/pwsh; read README.md.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 3 | 0 | 4/6 | 7.0 (6.7 to 7.3, 3 judged) | 0.0815 / 0.2445 |
| without_skill | 3 | 0 | 4.3/6 | 7.1 (7.0 to 7.3, 3 judged) | 0.0668 / 0.2004 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.0815 / 0.0681 | 0.0668 / 0.0665 | +0.0147 | +0.0016 |
| num_turns | 3 / 3 | 3 / 3 | 0 | 0 |
| duration_ms | 17740 / 18038 | 15235 / 15657 | +2505 | +2381 |
| input_tokens | 6 / 6 | 6 / 6 | 0 | 0 |
| output_tokens | 1039 / 1044 | 1038 / 1035 | +1 | +9 |
| cache_creation_input_tokens | 15433.3 / 11895 | 11675.3 / 11673 | +3758 | +222 |
| cache_read_input_tokens | 93656.7 / 97241 | 96979 / 96976 | -3322.3 | +265 |
| tool_errors | 0 / 0 | 0 / 0 | 0 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| exit-code-read | 0/3 | 0/3 |
| no-blind-third-try | 2/3 | 2/3 |
| exit-code-mapped | 3/3 | 3/3 |
| copy-untouched | 3/3 | 3/3 |
| reply-names-cause | 1/3 | 2/3 |
| stand-in-untouched | 3/3 | 3/3 |
