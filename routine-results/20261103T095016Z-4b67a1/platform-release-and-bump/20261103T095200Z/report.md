# Eval report: platform-release-and-bump

- Prompt: Bump this consumer to platform v0.1.104.
- Timestamp: 20261103T095200Z
- Run: billing subscription, runner routine, location cloud, id 20261103T095016Z-4b67a1; started 2026-11-03T09:52:00Z, ended 2026-11-03T09:55:57Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.38 to 0.38, from 4 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $1.96 over 4 call(s); agent $1.13, judge $0.83, guard $0.00; last agent call $0.55
- Harness: Claude Code `2.1.317 (Claude Code)`; models used: with_skill=claude-opus-5-5; without_skill=claude-haiku-5-5, claude-opus-5-5

| Arm | Objective | Judge overall | Cost (USD) | Turns | Duration (ms) | Error |
| --- | --- | --- | --- | --- | --- | --- |
| with_skill | 8/10 | 6.2 | 0.5811 | 11 | 48382 |  |
| without_skill | 8/10 | 6.2 | 0.5494 | 11 | 113624 |  |
