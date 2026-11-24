# Eval report: platform-release-and-bump

- Prompt: Bump this consumer to platform v0.1.104.
- Timestamp: 20261124T042131Z
- Run: billing subscription, runner routine, location cloud, id 20261124T042006Z-1d1445; started 2026-11-24T04:21:31Z, ended 2026-11-24T04:24:12Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.05 to 0.05, from 2 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $1.34 over 2 call(s); agent $1.34, judge $0.00, guard $0.00; last agent call $0.52
- Estimated allowance (approximate, from token counts by type, weight table 2026-11-20): 0.06 points of the weekly meter (0.04 to 0.10); Fable meter 0.00 points
- Harness: Claude Code `2.1.331 (Claude Code)`; models used: with_skill=claude-opus-5-5; without_skill=claude-haiku-5-5, claude-opus-5-5

| Arm | Objective | Judge overall | Cost (USD) | Turns | Duration (ms) | Error |
| --- | --- | --- | --- | --- | --- | --- |
| with_skill | 10/10 | skipped: the version with the skill passed more checks (10 of 10 vs 8 of 10) | 0.8138 | 16 | 66413 |  |
| without_skill | 8/10 | skipped: the version with the skill passed more checks (10 of 10 vs 8 of 10) | 0.5222 | 10 | 82440 |  |

Judge: when the version with the skill or guidance passes more checks than its partner, the judge isn't needed and both are skipped. On a tie or a loss, the judge scores both from 0 to 10.
