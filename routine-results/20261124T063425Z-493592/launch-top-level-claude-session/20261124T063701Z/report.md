# Eval report: launch-top-level-claude-session

- Timestamp: 20261124T063701Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261124T063425Z-493592; started 2026-11-24T06:37:01Z, ended 2026-11-24T06:38:19Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.05 to 0.05, from 6 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.42 over 6 call(s); agent $0.31, judge $0.11, guard $0.00; last agent call $0.07
- Estimated allowance (approximate, from token counts by type, weight table 2026-11-20): 0.02 points of the weekly meter (0.02 to 0.04); Fable meter 0.00 points

## Fixture: wsl-launch-login-path (n=3)

- Prompt: I'm in WSL. Open a new, separate top-level Claude Code session in a Windows Terminal tab, rooted in repos/example-api in this workspace, and seed it with this first message exactly: Triage issue #5; it has evidence in docs/notes.md. Stand by. Leave it running for me to drive. wt.exe and pwsh.exe here are the stand-ins in bin/.
- Harness: Claude Code `2.1.331 (Claude Code)`; models used: without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| without_skill | 3 | 0 | 3.7/8 | 4.4 (4.2 to 4.6, 3 judged) | 0.1043 / 0.3130 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did):

| Metric (mean / median) | without_skill |
| --- | --- |
| cost_usd | 0.1043 / 0.0716 |
| num_turns | 4 / 4 |
| duration_ms | 14676 / 14577 |
| input_tokens | 8 / 8 |
| output_tokens | 1294.7 / 1295 |
| cache_creation_input_tokens | 19508.7 / 10055 |
| cache_read_input_tokens | 133321 / 143045 |
| tool_errors | 0.3 / 0 |

| Check (passed / scored) | without_skill |
| --- | --- |
| launched-in-wt-rooted-in-the-repo | 3/3 |
| child-marker-cleared-and-persistence-forced | 0/3 |
| login-path-injected | 0/3 |
| claude-by-absolute-path | 0/3 |
| prompt-one-argument-semicolon-escaped | 2/3 |
| session-stays-interactive | 3/3 |
| reply-says-how-to-verify | 0/3 |
| stand-ins-untouched | 3/3 |
