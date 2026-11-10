# Eval report: tool-powershell

- Timestamp: 20261110T215002Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261110T214848Z-21cbbf; started 2026-11-10T21:50:02Z, ended 2026-11-10T21:51:47Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.29 to 0.29, from 6 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.72 over 6 call(s); agent $0.54, judge $0.18, guard $0.00; last agent call $0.15

## Fixture: installer-exit-3010 (n=3)

- Prompt: The rollout task marks scripts/install-agent.ps1 as failed on every machine: it exits with code 1 and prints nothing, yet the agent is installed. Find out why and make the task stop failing when nothing is wrong. PowerShell here is the stand-in bin/pwsh; read README.md.
- Harness: Claude Code `2.1.322 (Claude Code)`; models used: without_skill=claude-opus-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| without_skill | 3 | 0 | 6/6 | 9.2 (9.0 to 9.3, 3 judged) | 0.1802 / 0.5407 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did):

| Metric (mean / median) | without_skill |
| --- | --- |
| cost_usd | 0.1802 / 0.1458 |
| num_turns | 5.7 / 6 |
| duration_ms | 26192 / 27648 |
| input_tokens | 10.7 / 12 |
| output_tokens | 2127 / 2270 |
| cache_creation_input_tokens | 20241.3 / 11333 |
| cache_read_input_tokens | 182250.7 / 216622 |
| tool_errors | 0 / 0 |

| Check (passed / scored) | without_skill |
| --- | --- |
| exit-code-read | 3/3 |
| no-blind-third-try | 3/3 |
| reboot-code-accepted | 3/3 |
| install-untouched | 3/3 |
| reply-names-cause | 3/3 |
| stand-in-untouched | 3/3 |
