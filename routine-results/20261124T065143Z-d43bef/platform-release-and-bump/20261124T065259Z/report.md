# Eval report: platform-release-and-bump

- Prompt: Bump this consumer to platform v0.1.104.
- Timestamp: 20261124T065259Z
- Run: billing subscription, runner routine, location cloud, id 20261124T065143Z-d43bef; started 2026-11-24T06:52:59Z, ended 2026-11-24T06:55:47Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.05 to 0.05, from 4 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $1.48 over 4 call(s); agent $1.14, judge $0.34, guard $0.00; last agent call $0.44
- Estimated allowance (approximate, from token counts by type, weight table 2026-11-20): 0.08 points of the weekly meter (0.06 to 0.11); Fable meter 0.04 points
- Harness: Claude Code `2.1.331 (Claude Code)`; models used: with_skill=claude-haiku-5-5, claude-opus-5-5; without_skill=claude-opus-5-5

| Arm | Objective | Judge overall | Cost (USD) | Turns | Duration (ms) | Error |
| --- | --- | --- | --- | --- | --- | --- |
| with_skill | 8/10 | 4.4 | 0.7066 | 13 | 90693 |  |
| without_skill | 8/10 | 5.3 | 0.4353 | 11 | 49416 |  |
