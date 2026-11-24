# Eval report: platform-release-and-bump

- Prompt: Bump this consumer to platform v0.1.104.
- Timestamp: 20261124T061341Z
- Run: billing subscription, runner routine, location cloud, id 20261124T061219Z-556f17; started 2026-11-24T06:13:41Z, ended 2026-11-24T06:15:58Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.05 to 0.05, from 4 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $1.40 over 4 call(s); agent $1.05, judge $0.36, guard $0.00; last agent call $0.44
- Estimated allowance (approximate, from token counts by type, weight table 2026-11-20): 0.07 points of the weekly meter (0.05 to 0.10); Fable meter 0.04 points
- Harness: Claude Code `2.1.331 (Claude Code)`; models used: with_skill=claude-opus-5-5; without_skill=claude-opus-5-5

| Arm | Objective | Judge overall | Cost (USD) | Turns | Duration (ms) | Error |
| --- | --- | --- | --- | --- | --- | --- |
| with_skill | 8/10 | 5.3 | 0.6067 | 12 | 49397 |  |
| without_skill | 8/10 | 4.9 | 0.4388 | 10 | 54828 |  |
