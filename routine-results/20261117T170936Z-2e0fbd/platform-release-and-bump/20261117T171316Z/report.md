# Eval report: platform-release-and-bump

- Prompt: Bump this consumer to platform v0.1.104.
- Timestamp: 20261117T171316Z
- Run: billing subscription, runner routine, location cloud, id 20261117T170936Z-2e0fbd; started 2026-11-17T17:13:16Z, ended 2026-11-17T17:14:50Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.12 to 0.12, from 2 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.37 over 2 call(s); agent $0.37, judge $0.00, guard $0.00; last agent call $0.15
- Harness: Claude Code `2.1.326 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | Objective | Judge overall | Cost (USD) | Turns | Duration (ms) | Error |
| --- | --- | --- | --- | --- | --- | --- |
| with_skill | 10/10 | skipped: the version with the skill passed more checks (10 of 10 vs 9 of 10) | 0.2209 | 13 | 43938 |  |
| without_skill | 9/10 | skipped: the version with the skill passed more checks (10 of 10 vs 9 of 10) | 0.1521 | 12 | 39949 |  |

Judge: when the version with the skill or guidance passes more checks than its partner, the judge isn't needed and both are skipped. On a tie or a loss, the judge scores both from 0 to 10.
