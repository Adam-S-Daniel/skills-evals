# Eval report: platform-release-and-bump

- Prompt: Bump this consumer to platform v0.1.104.
- Timestamp: 20261124T002556Z
- Run: billing subscription, runner routine, location cloud, id 20261124T002103Z-5ac87a; started 2026-11-24T00:25:56Z, ended 2026-11-24T00:28:13Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.03 to 0.03, from 4 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.72 over 4 call(s); agent $0.52, judge $0.21, guard $0.00; last agent call $0.17
- Estimated allowance (approximate, from token counts by type, weight table 2026-11-20): 0.04 points of the weekly meter (0.03 to 0.07); Fable meter 0.00 points
- Harness: Claude Code `2.1.331 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | Objective | Judge overall | Cost (USD) | Turns | Duration (ms) | Error |
| --- | --- | --- | --- | --- | --- | --- |
| with_skill | 10/10 | 7.3 | 0.3414 | 16 | 63079 |  |
| without_skill | 10/10 | 9.0 | 0.1738 | 11 | 35252 |  |
