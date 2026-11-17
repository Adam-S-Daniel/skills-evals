# Eval report: platform-release-and-bump

- Prompt: Bump this consumer to platform v0.1.104.
- Timestamp: 20261117T221009Z
- Run: billing subscription, runner routine, location cloud, id 20261117T220846Z-e42703; started 2026-11-17T22:10:09Z, ended 2026-11-17T22:12:06Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.15 to 0.15, from 2 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.85 over 2 call(s); agent $0.85, judge $0.00, guard $0.00; last agent call $0.33
- Harness: Claude Code `2.1.326 (Claude Code)`; models used: with_skill=claude-opus-5-5; without_skill=claude-opus-5-5

| Arm | Objective | Judge overall | Cost (USD) | Turns | Duration (ms) | Error |
| --- | --- | --- | --- | --- | --- | --- |
| with_skill | 10/10 | skipped: the version with the skill passed more checks (10 of 10 vs 8 of 10) | 0.5204 | 11 | 57950 |  |
| without_skill | 8/10 | skipped: the version with the skill passed more checks (10 of 10 vs 8 of 10) | 0.3264 | 9 | 46952 |  |

Judge: when the version with the skill or guidance passes more checks than its partner, the judge isn't needed and both are skipped. On a tie or a loss, the judge scores both from 0 to 10.
