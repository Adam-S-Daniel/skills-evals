# Eval report: launch-top-level-claude-session

- Timestamp: 20261124T113550Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261124T113427Z-8a73a4; started 2026-11-24T11:35:50Z, ended 2026-11-24T11:36:54Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.07 to 0.07, from 4 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.31 over 4 call(s); agent $0.24, judge $0.07, guard $0.00; last agent call $0.08
- Estimated allowance (approximate, from token counts by type, weight table 2026-11-20): 0.02 points of the weekly meter (0.01 to 0.03); Fable meter 0.00 points

## Fixture: wsl-launch-login-path (n=1)

- Prompt: I'm in WSL. Open a new, separate top-level Claude Code session in a Windows Terminal tab, rooted in repos/example-api in this workspace, and seed it with this first message exactly: Triage issue #5; it has evidence in docs/notes.md. Stand by. Leave it running for me to drive. wt.exe and pwsh.exe here are the stand-ins in bin/.
- Harness: Claude Code `2.1.331 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 2/8 | 6.2 (6.2 to 6.2, 1 judged) | 0.1555 / 0.1555 |
| without_skill | 1 | 0 | 4/8 | 5.0 (5.0 to 5.0, 1 judged) | 0.0826 / 0.0826 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1555 / 0.1555 | 0.0826 / 0.0826 | +0.0729 | +0.0729 |
| num_turns | 6 / 6 | 4 / 4 | +2 | +2 |
| duration_ms | 19827 / 19827 | 18117 / 18117 | +1710 | +1710 |
| input_tokens | 12 / 12 | 8 / 8 | +4 | +4 |
| output_tokens | 1450 / 1450 | 1654 / 1654 | -204 | -204 |
| cache_creation_input_tokens | 30644 / 30644 | 13058 / 13058 | +17586 | +17586 |
| cache_read_input_tokens | 184474 / 184474 | 138320 / 138320 | +46154 | +46154 |
| tool_errors | 0 / 0 | 0 / 0 | 0 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| launched-in-wt-rooted-in-the-repo | 0/1 | 1/1 |
| child-marker-cleared-and-persistence-forced | 0/1 | 0/1 |
| login-path-injected | 0/1 | 0/1 |
| claude-by-absolute-path | 0/1 | 0/1 |
| prompt-one-argument-semicolon-escaped | 0/1 | 1/1 |
| session-stays-interactive | 0/1 | 1/1 |
| reply-says-how-to-verify | 1/1 | 0/1 |
| stand-ins-untouched | 1/1 | 1/1 |
