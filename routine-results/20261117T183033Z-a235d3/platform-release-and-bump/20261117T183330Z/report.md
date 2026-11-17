# Eval report: platform-release-and-bump

- Prompt: Bump this consumer to platform v0.1.104.
- Timestamp: 20261117T183330Z
- Run: billing subscription, runner routine, location cloud, id 20261117T183033Z-a235d3; started 2026-11-17T18:33:30Z, ended 2026-11-17T18:36:08Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.12 to 0.12, from 4 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $1.19 over 4 call(s); agent $0.90, judge $0.28, guard $0.00; last agent call $0.35
- Harness: Claude Code `2.1.326 (Claude Code)`; models used: with_skill=claude-opus-5-5; without_skill=claude-opus-5-5

| Arm | Objective | Judge overall | Cost (USD) | Turns | Duration (ms) | Error |
| --- | --- | --- | --- | --- | --- | --- |
| with_skill | 8/10 | 5.1 | 0.5502 | 12 | 59774 |  |
| without_skill | 8/10 | 5.3 | 0.3533 | 11 | 56990 |  |
