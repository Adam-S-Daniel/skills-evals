# Eval report: launch-top-level-claude-session

- Timestamp: 20261124T185124Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261124T184825Z-795d7b; started 2026-11-24T18:51:24Z, ended 2026-11-24T18:52:07Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.1 to 0.1, from 2 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.23 over 2 call(s); agent $0.23, judge $0.00, guard $0.00; last agent call $0.07
- Estimated allowance (approximate, from token counts by type, weight table 2026-11-20): 0.01 points of the weekly meter (0.01 to 0.02); Fable meter 0.00 points

## Fixture: wsl-launch-login-path (n=1)

- Prompt: I'm in WSL. Open a new, separate top-level Claude Code session in a Windows Terminal tab, rooted in repos/example-api in this workspace, and seed it with this first message exactly: Triage issue #5; it has evidence in docs/notes.md. Stand by. Leave it running for me to drive. wt.exe and pwsh.exe here are the stand-ins in bin/.
- Harness: Claude Code `2.1.331 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 8/8 | skipped: the version with the skill passed more checks (8 of 8 vs 3 of 8) | 0.1563 / 0.1563 |
| without_skill | 1 | 0 | 3/8 | skipped: the version with the skill passed more checks (8 of 8 vs 3 of 8) | 0.0718 / 0.0718 |

Judge: when the version with the skill or guidance passes more checks than its partner, the judge isn't needed and both are skipped. On a tie or a loss, the judge scores both from 0 to 10.

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1563 / 0.1563 | 0.0718 / 0.0718 | +0.0845 | +0.0845 |
| num_turns | 6 / 6 | 4 / 4 | +2 | +2 |
| duration_ms | 19806 / 19806 | 13713 / 13713 | +6093 | +6093 |
| input_tokens | 12 / 12 | 8 / 8 | +4 | +4 |
| output_tokens | 1470 / 1470 | 1070 / 1070 | +400 | +400 |
| cache_creation_input_tokens | 30783 / 30783 | 11857 / 11857 | +18926 | +18926 |
| cache_read_input_tokens | 184695 / 184695 | 136352 / 136352 | +48343 | +48343 |
| tool_errors | 0 / 0 | 1 / 1 | -1 | -1 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| launched-in-wt-rooted-in-the-repo | 1/1 | 1/1 |
| child-marker-cleared-and-persistence-forced | 1/1 | 0/1 |
| login-path-injected | 1/1 | 0/1 |
| claude-by-absolute-path | 1/1 | 0/1 |
| prompt-one-argument-semicolon-escaped | 1/1 | 0/1 |
| session-stays-interactive | 1/1 | 1/1 |
| reply-says-how-to-verify | 1/1 | 0/1 |
| stand-ins-untouched | 1/1 | 1/1 |
