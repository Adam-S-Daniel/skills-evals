# Eval report: platform-release-and-bump

- Prompt: Bump this consumer to platform v0.1.104.
- Timestamp: 20261117T213046Z
- Run: billing subscription, runner routine, location cloud, id 20261117T212712Z-cf3096; started 2026-11-17T21:30:46Z, ended 2026-11-17T21:32:02Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.15 to 0.15, from 2 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.32 over 2 call(s); agent $0.32, judge $0.00, guard $0.00; last agent call $0.11
- Harness: Claude Code `2.1.326 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | Objective | Judge overall | Cost (USD) | Turns | Duration (ms) | Error |
| --- | --- | --- | --- | --- | --- | --- |
| with_skill | 10/10 | skipped: the version with the skill passed more checks (10 of 10 vs 9 of 10) | 0.2054 | 12 | 40046 |  |
| without_skill | 9/10 | skipped: the version with the skill passed more checks (10 of 10 vs 9 of 10) | 0.1133 | 9 | 24465 |  |

Judge: when the version with the skill or guidance passes more checks than its partner, the judge isn't needed and both are skipped. On a tie or a loss, the judge scores both from 0 to 10.
