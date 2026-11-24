# Eval report: launch-top-level-claude-session

- Timestamp: 20261124T063509Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261124T063425Z-493592; started 2026-11-24T06:35:09Z, ended 2026-11-24T06:37:00Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.05 to 0.05, from 6 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.91 over 6 call(s); agent $0.72, judge $0.20, guard $0.00; last agent call $0.15
- Estimated allowance (approximate, from token counts by type, weight table 2026-11-20): 0.04 points of the weekly meter (0.03 to 0.07); Fable meter 0.03 points

## Fixture: wsl-launch-login-path (n=3)

- Prompt: I'm in WSL. Open a new, separate top-level Claude Code session in a Windows Terminal tab, rooted in repos/example-api in this workspace, and seed it with this first message exactly: Triage issue #5; it has evidence in docs/notes.md. Stand by. Leave it running for me to drive. wt.exe and pwsh.exe here are the stand-ins in bin/.
- Harness: Claude Code `2.1.331 (Claude Code)`; models used: without_skill=claude-opus-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| without_skill | 3 | 0 | 4.7/8 | 4.8 (4.8 to 4.8, 3 judged) | 0.2387 / 0.7162 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did):

| Metric (mean / median) | without_skill |
| --- | --- |
| cost_usd | 0.2387 / 0.1527 |
| num_turns | 4.3 / 4 |
| duration_ms | 25695.3 / 22845 |
| input_tokens | 8.7 / 8 |
| output_tokens | 2219.3 / 1944 |
| cache_creation_input_tokens | 20598 / 10609 |
| cache_read_input_tokens | 147687.3 / 144546 |
| tool_errors | 0 / 0 |

| Check (passed / scored) | without_skill |
| --- | --- |
| launched-in-wt-rooted-in-the-repo | 3/3 |
| child-marker-cleared-and-persistence-forced | 0/3 |
| login-path-injected | 0/3 |
| claude-by-absolute-path | 2/3 |
| prompt-one-argument-semicolon-escaped | 3/3 |
| session-stays-interactive | 3/3 |
| reply-says-how-to-verify | 0/3 |
| stand-ins-untouched | 3/3 |
