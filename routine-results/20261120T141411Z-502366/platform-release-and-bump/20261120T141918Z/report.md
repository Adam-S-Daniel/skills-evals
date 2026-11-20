# Eval report: platform-release-and-bump

- Prompt: Bump this consumer to platform v0.1.104.
- Timestamp: 20261120T141918Z
- Run: billing subscription, runner routine, location cloud, id 20261120T141411Z-502366; started 2026-11-20T14:19:18Z, ended 2026-11-20T14:20:37Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.74 to 0.74, from 4 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.41 over 4 call(s); agent $0.29, judge $0.12, guard $0.00; last agent call $0.12
- Estimated allowance (approximate, from token counts by type, weight table 2026-11-20): 0.03 points of the weekly meter (0.03 to 0.03); Fable meter 0.00 points
- Harness: Claude Code `2.1.329 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | Objective | Judge overall | Cost (USD) | Turns | Duration (ms) | Error |
| --- | --- | --- | --- | --- | --- | --- |
| with_skill | 7/10 | 3.8 | 0.1717 | 8 | 24206 |  |
| without_skill | 9/10 | 4.6 | 0.1215 | 9 | 30063 |  |
