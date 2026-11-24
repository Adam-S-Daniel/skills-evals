# Eval report: platform-release-and-bump

- Prompt: Bump this consumer to platform v0.1.104.
- Timestamp: 20261124T014731Z
- Run: billing subscription, runner routine, location cloud, id 20261124T014454Z-06537e; started 2026-11-24T01:47:31Z, ended 2026-11-24T01:49:26Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.04 to 0.04, from 2 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $1.07 over 2 call(s); agent $1.07, judge $0.00, guard $0.00; last agent call $0.39
- Estimated allowance (approximate, from token counts by type, weight table 2026-11-20): 0.05 points of the weekly meter (0.03 to 0.08); Fable meter 0.00 points
- Harness: Claude Code `2.1.331 (Claude Code)`; models used: with_skill=claude-opus-5-5; without_skill=claude-haiku-5-5, claude-opus-5-5

| Arm | Objective | Judge overall | Cost (USD) | Turns | Duration (ms) | Error |
| --- | --- | --- | --- | --- | --- | --- |
| with_skill | 8/10 | skipped: the version with the skill passed more checks (8 of 10 vs 7 of 10) | 0.6736 | 10 | 43530 |  |
| without_skill | 7/10 | skipped: the version with the skill passed more checks (8 of 10 vs 7 of 10) | 0.3938 | 7 | 60366 |  |

Judge: when the version with the skill or guidance passes more checks than its partner, the judge isn't needed and both are skipped. On a tie or a loss, the judge scores both from 0 to 10.
