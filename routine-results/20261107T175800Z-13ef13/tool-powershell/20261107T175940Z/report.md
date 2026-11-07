# Eval report: tool-powershell

- Timestamp: 20261107T175940Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261107T175800Z-13ef13; started 2026-11-07T17:59:40Z, ended 2026-11-07T18:04:46Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.58 to 0.59, from 13 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $1.85 over 12 call(s); agent $1.26, judge $0.59, guard $0.00; last agent call $0.19

## Fixture: robocopy-exit-one (n=3)

- Prompt: The nightly task marks scripts/mirror-exports.ps1 as failed: it exits with code 1 and prints nothing, yet D:\backup\export looks current. Find out why and make the task stop failing when nothing is wrong. PowerShell here is the stand-in bin/pwsh; read README.md.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-opus-5-5; without_skill=claude-opus-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 3 | 0 | 4.3/6 | 9.0 (8.7 to 9.3, 3 judged) | 0.2232 / 0.6696 |
| without_skill | 3 | 0 | 4.7/6 | 9.0 (9.0 to 9.0, 3 judged) | 0.1964 / 0.5892 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.2232 / 0.2183 | 0.1964 / 0.1880 | +0.0268 | +0.0302 |
| num_turns | 6.3 / 7 | 7 / 6 | -0.7 | +1 |
| duration_ms | 34975.3 / 35357 | 37249.7 / 33521 | -2274.3 | +1836 |
| input_tokens | 11.3 / 12 | 12 / 12 | -0.7 | 0 |
| output_tokens | 2219 / 2547 | 2249.7 / 2232 | -30.7 | +315 |
| cache_creation_input_tokens | 17497.3 / 14645 | 13675.3 / 13643 | +3822 | +1002 |
| cache_read_input_tokens | 194045.7 / 197484 | 209855 / 209868 | -15809.3 | -12384 |
| tool_errors | 0 / 0 | 0 / 0 | 0 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| exit-code-read | 2/3 | 3/3 |
| no-blind-third-try | 2/3 | 2/3 |
| exit-code-mapped | 3/3 | 3/3 |
| copy-untouched | 3/3 | 3/3 |
| reply-names-cause | 0/3 | 0/3 |
| stand-in-untouched | 3/3 | 3/3 |
