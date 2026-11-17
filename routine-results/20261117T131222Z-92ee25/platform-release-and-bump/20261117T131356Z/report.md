# Eval report: platform-release-and-bump

- Prompt: Bump this consumer to platform v0.1.104.
- Timestamp: 20261117T131356Z
- Run: billing subscription, runner routine, location cloud, id 20261117T131222Z-92ee25; started 2026-11-17T13:13:56Z, ended 2026-11-17T13:16:26Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.08 to 0.08, from 4 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.51 over 4 call(s); agent $0.36, judge $0.15, guard $0.00; last agent call $0.14
- Harness: Claude Code `2.1.326 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | Objective | Judge overall | Cost (USD) | Turns | Duration (ms) | Error |
| --- | --- | --- | --- | --- | --- | --- |
| with_skill | 10/10 | 7.8 | 0.2180 | 13 | 48833 |  |
| without_skill | 10/10 | 6.3 | 0.1427 | 10 | 50791 |  |
