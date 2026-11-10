# Eval report: tool-powershell

- Timestamp: 20261110T215148Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261110T214848Z-21cbbf; started 2026-11-10T21:51:48Z, ended 2026-11-10T21:52:59Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.29 to 0.29, from 6 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.28 over 6 call(s); agent $0.21, judge $0.07, guard $0.00; last agent call $0.04

## Fixture: installer-exit-3010 (n=3)

- Prompt: The rollout task marks scripts/install-agent.ps1 as failed on every machine: it exits with code 1 and prints nothing, yet the agent is installed. Find out why and make the task stop failing when nothing is wrong. PowerShell here is the stand-in bin/pwsh; read README.md.
- Harness: Claude Code `2.1.322 (Claude Code)`; models used: without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| without_skill | 3 | 0 | 4/6 | 9.3 (9.3 to 9.3, 3 judged) | 0.0689 / 0.2067 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did):

| Metric (mean / median) | without_skill |
| --- | --- |
| cost_usd | 0.0689 / 0.0509 |
| num_turns | 3.3 / 3 |
| duration_ms | 15293.3 / 15171 |
| input_tokens | 6.7 / 6 |
| output_tokens | 1129.7 / 1100 |
| cache_creation_input_tokens | 18805.7 / 9385 |
| cache_read_input_tokens | 105772.3 / 102837 |
| tool_errors | 0 / 0 |

| Check (passed / scored) | without_skill |
| --- | --- |
| exit-code-read | 0/3 |
| no-blind-third-try | 0/3 |
| reboot-code-accepted | 3/3 |
| install-untouched | 3/3 |
| reply-names-cause | 3/3 |
| stand-in-untouched | 3/3 |
