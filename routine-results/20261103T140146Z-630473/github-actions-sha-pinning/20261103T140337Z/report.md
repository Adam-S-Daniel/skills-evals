# Eval report: github-actions-sha-pinning

- Prompt: Bring this repo's action pins into line with the pinning policy.
- Timestamp: 20261103T140337Z
- Run: billing subscription, runner routine, location cloud, id 20261103T140146Z-630473; started 2026-11-03T14:03:37Z, ended 2026-11-03T14:05:18Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.45 to 0.45, from 4 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.42 over 4 call(s); agent $0.27, judge $0.14, guard $0.00; last agent call $0.11
- Harness: Claude Code `2.1.317 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | Objective | Judge overall | Cost (USD) | Turns | Duration (ms) | Error |
| --- | --- | --- | --- | --- | --- | --- |
| with_skill | 10/10 | 8.8 | 0.1607 | 7 | 40873 |  |
| without_skill | 10/10 | 8.1 | 0.1108 | 7 | 38763 |  |
