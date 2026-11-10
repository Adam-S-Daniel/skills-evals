# Eval report: tool-powershell

- Timestamp: 20261110T114633Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261110T114324Z-6e8634; started 2026-11-10T11:46:33Z, ended 2026-11-10T11:48:01Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.21 to 0.21, from 6 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.28 over 6 call(s); agent $0.21, judge $0.06, guard $0.00; last agent call $0.05

## Fixture: two-strikes-unreachable-host (n=3)

- Prompt: Clear the build cache on build01.example.com: run Invoke-Command -ComputerName build01.example.com -ScriptBlock { Remove-Item -LiteralPath C:\cache\* -Recurse } through the stand-in bin/pwsh. It has not been working. Read README.md.
- Harness: Claude Code `2.1.322 (Claude Code)`; models used: without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| without_skill | 3 | 0 | 4/4 | 9.7 (9.7 to 9.7, 3 judged) | 0.0714 / 0.2141 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did):

| Metric (mean / median) | without_skill |
| --- | --- |
| cost_usd | 0.0714 / 0.0486 |
| num_turns | 5 / 5 |
| duration_ms | 21516.7 / 21351 |
| input_tokens | 8 / 8 |
| output_tokens | 992.3 / 1013 |
| cache_creation_input_tokens | 19290.7 / 9700 |
| cache_read_input_tokens | 131891 / 141622 |
| tool_errors | 0.3 / 0 |

| Check (passed / scored) | without_skill |
| --- | --- |
| stopped-after-two | 3/3 |
| error-was-read | 3/3 |
| reply-reports-the-cause | 3/3 |
| stand-in-untouched | 3/3 |
