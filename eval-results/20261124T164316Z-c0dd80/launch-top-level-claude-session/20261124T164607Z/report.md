# Eval report: launch-top-level-claude-session

- Timestamp: 20261124T164607Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261124T164316Z-c0dd80; started 2026-11-24T16:46:07Z, ended 2026-11-24T16:47:06Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.09 to 0.09, from 4 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.30 over 4 call(s); agent $0.23, judge $0.06, guard $0.00; last agent call $0.08
- Estimated allowance (approximate, from token counts by type, weight table 2026-11-20): 0.02 points of the weekly meter (0.01 to 0.03); Fable meter 0.00 points

## Fixture: wsl-launch-login-path (n=1)

- Prompt: I'm in WSL. Open a new, separate top-level Claude Code session in a Windows Terminal tab, rooted in repos/example-api in this workspace, and seed it with this first message exactly: Triage issue #5; it has evidence in docs/notes.md. Stand by. Leave it running for me to drive. wt.exe and pwsh.exe here are the stand-ins in bin/.
- Harness: Claude Code `2.1.331 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 2/8 | 6.8 (6.8 to 6.8, 1 judged) | 0.1559 / 0.1559 |
| without_skill | 1 | 0 | 3/8 | 4.0 (4.0 to 4.0, 1 judged) | 0.0773 / 0.0773 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1559 / 0.1559 | 0.0773 / 0.0773 | +0.0786 | +0.0786 |
| num_turns | 6 / 6 | 4 / 4 | +2 | +2 |
| duration_ms | 16827 / 16827 | 17207 / 17207 | -380 | -380 |
| input_tokens | 12 / 12 | 8 / 8 | +4 | +4 |
| output_tokens | 1493 / 1493 | 1480 / 1480 | +13 | +13 |
| cache_creation_input_tokens | 30616 / 30616 | 12208 / 12208 | +18408 | +18408 |
| cache_read_input_tokens | 184619 / 184619 | 136306 / 136306 | +48313 | +48313 |
| tool_errors | 0 / 0 | 0 / 0 | 0 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| launched-in-wt-rooted-in-the-repo | 0/1 | 1/1 |
| child-marker-cleared-and-persistence-forced | 0/1 | 0/1 |
| login-path-injected | 0/1 | 0/1 |
| claude-by-absolute-path | 0/1 | 0/1 |
| prompt-one-argument-semicolon-escaped | 0/1 | 0/1 |
| session-stays-interactive | 0/1 | 1/1 |
| reply-says-how-to-verify | 1/1 | 0/1 |
| stand-ins-untouched | 1/1 | 1/1 |
