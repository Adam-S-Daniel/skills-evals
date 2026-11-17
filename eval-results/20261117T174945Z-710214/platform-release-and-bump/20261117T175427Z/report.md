# Eval report: platform-release-and-bump

- Prompt: Bump this consumer to platform v0.1.104.
- Timestamp: 20261117T175427Z
- Run: billing subscription, runner routine, location cloud, id 20261117T174945Z-710214; started 2026-11-17T17:54:27Z, ended 2026-11-17T17:56:13Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.12 to 0.12, from 4 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.49 over 4 call(s); agent $0.35, judge $0.14, guard $0.00; last agent call $0.13
- Harness: Claude Code `2.1.326 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | Objective | Judge overall | Cost (USD) | Turns | Duration (ms) | Error |
| --- | --- | --- | --- | --- | --- | --- |
| with_skill | 10/10 | 8.3 | 0.2256 | 13 | 41925 |  |
| without_skill | 10/10 | 6.7 | 0.1266 | 9 | 28315 |  |
