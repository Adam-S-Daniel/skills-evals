# Eval report: platform-release-and-bump

- Prompt: Bump this consumer to platform v0.1.104.
- Timestamp: 20261117T151953Z
- Run: billing subscription, runner routine, location cloud, id 20261117T151817Z-c95b17; started 2026-11-17T15:19:53Z, ended 2026-11-17T15:21:45Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.1 to 0.1, from 4 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.47 over 4 call(s); agent $0.33, judge $0.14, guard $0.00; last agent call $0.12
- Harness: Claude Code `2.1.326 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | Objective | Judge overall | Cost (USD) | Turns | Duration (ms) | Error |
| --- | --- | --- | --- | --- | --- | --- |
| with_skill | 10/10 | 6.8 | 0.2110 | 12 | 44015 |  |
| without_skill | 10/10 | 8.0 | 0.1215 | 9 | 31148 |  |
