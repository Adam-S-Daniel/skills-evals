# Eval report: platform-release-and-bump

- Prompt: Bump this consumer to platform v0.1.104.
- Timestamp: 20261117T221207Z
- Run: billing subscription, runner routine, location cloud, id 20261117T220846Z-e42703; started 2026-11-17T22:12:07Z, ended 2026-11-17T22:13:52Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.15 to 0.15, from 4 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.48 over 4 call(s); agent $0.34, judge $0.15, guard $0.00; last agent call $0.12
- Harness: Claude Code `2.1.326 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | Objective | Judge overall | Cost (USD) | Turns | Duration (ms) | Error |
| --- | --- | --- | --- | --- | --- | --- |
| with_skill | 10/10 | 9.0 | 0.2195 | 13 | 38265 |  |
| without_skill | 10/10 | 5.7 | 0.1166 | 8 | 24439 |  |
