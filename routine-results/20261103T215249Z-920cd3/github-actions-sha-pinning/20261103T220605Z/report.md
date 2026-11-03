# Eval report: github-actions-sha-pinning

- Prompt: Bring this repo's action pins into line with the pinning policy.
- Timestamp: 20261103T220605Z
- Run: billing subscription, runner routine, location cloud, id 20261103T215249Z-920cd3; started 2026-11-03T22:06:05Z, ended 2026-11-03T22:08:43Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.76 to 0.76, from 2 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.81 over 2 call(s); agent $0.81, judge $0.00, guard $0.00; last agent call $0.35
- Harness: Claude Code `2.1.317 (Claude Code)`; models used: with_skill=claude-haiku-5-5, claude-opus-5-5; without_skill=claude-haiku-5-5, claude-opus-5-5

| Arm | Objective | Judge overall | Cost (USD) | Turns | Duration (ms) | Error |
| --- | --- | --- | --- | --- | --- | --- |
| with_skill | 10/10 | skipped (objective-decided) | 0.4585 | 9 | 78718 |  |
| without_skill | 7/10 | skipped (objective-decided) | 0.3548 | 8 | 75219 |  |
