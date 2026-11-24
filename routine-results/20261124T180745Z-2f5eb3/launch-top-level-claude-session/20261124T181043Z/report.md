# Eval report: launch-top-level-claude-session

- Timestamp: 20261124T181043Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261124T180745Z-2f5eb3; started 2026-11-24T18:10:43Z, ended 2026-11-24T18:12:04Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.1 to 0.1, from 2 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.27 over 2 call(s); agent $0.27, judge $0.00, guard $0.00; last agent call $0.08
- Estimated allowance (approximate, from token counts by type, weight table 2026-11-20): 0.02 points of the weekly meter (0.01 to 0.03); Fable meter 0.00 points

## Fixture: wsl-launch-login-path (n=1)

- Prompt: I'm in WSL. Open a new, separate top-level Claude Code session in a Windows Terminal tab, rooted in repos/example-api in this workspace, and seed it with this first message exactly: Triage issue #5; it has evidence in docs/notes.md. Stand by. Leave it running for me to drive. wt.exe and pwsh.exe here are the stand-ins in bin/.
- Harness: Claude Code `2.1.331 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 8/8 | skipped: the version with the skill passed more checks (8 of 8 vs 4 of 8) | 0.1903 / 0.1903 |
| without_skill | 1 | 0 | 4/8 | skipped: the version with the skill passed more checks (8 of 8 vs 4 of 8) | 0.0758 / 0.0758 |

Judge: when the version with the skill or guidance passes more checks than its partner, the judge isn't needed and both are skipped. On a tie or a loss, the judge scores both from 0 to 10.

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1903 / 0.1903 | 0.0758 / 0.0758 | +0.1144 | +0.1144 |
| num_turns | 9 / 9 | 4 / 4 | +5 | +5 |
| duration_ms | 57086 / 57086 | 14412 / 14412 | +42674 | +42674 |
| input_tokens | 18 / 18 | 8 / 8 | +10 | +10 |
| output_tokens | 2575 / 2575 | 1374 / 1374 | +1201 | +1201 |
| cache_creation_input_tokens | 32981 / 32981 | 12105 / 12105 | +20876 | +20876 |
| cache_read_input_tokens | 325633 / 325633 | 136489 / 136489 | +189144 | +189144 |
| tool_errors | 0 / 0 | 1 / 1 | -1 | -1 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| launched-in-wt-rooted-in-the-repo | 1/1 | 1/1 |
| child-marker-cleared-and-persistence-forced | 1/1 | 0/1 |
| login-path-injected | 1/1 | 0/1 |
| claude-by-absolute-path | 1/1 | 0/1 |
| prompt-one-argument-semicolon-escaped | 1/1 | 1/1 |
| session-stays-interactive | 1/1 | 1/1 |
| reply-says-how-to-verify | 1/1 | 0/1 |
| stand-ins-untouched | 1/1 | 1/1 |
