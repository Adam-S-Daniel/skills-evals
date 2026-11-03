# Eval report: github-actions-sha-pinning

- Prompt: Bring this repo's action pins into line with the pinning policy.
- Timestamp: 20261103T233502Z
- Run: billing subscription, runner routine, location cloud, id 20261103T233333Z-040d9b; started 2026-11-03T23:35:02Z, ended 2026-11-03T23:36:57Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.8 to 0.8, from 4 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $1.03 over 4 call(s); agent $0.67, judge $0.36, guard $0.00; last agent call $0.28
- Harness: Claude Code `2.1.317 (Claude Code)`; models used: with_skill=claude-opus-5-5; without_skill=claude-opus-5-5

| Arm | Objective | Judge overall | Cost (USD) | Turns | Duration (ms) | Error |
| --- | --- | --- | --- | --- | --- | --- |
| with_skill | 8/10 | 9.3 | 0.3957 | 7 | 44633 |  |
| without_skill | 10/10 | 9.7 | 0.2761 | 5 | 48712 |  |
