# Eval report: github-actions-sha-pinning

- Prompt: Bring this repo's action pins into line with the pinning policy.
- Timestamp: 20261103T184536Z
- Run: billing subscription, runner routine, location cloud, id 20261103T182223Z-b99a1a; started 2026-11-03T18:45:36Z, ended 2026-11-03T18:48:29Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.66 to 0.66, from 2 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.82 over 2 call(s); agent $0.82, judge $0.00, guard $0.00; last agent call $0.37
- Harness: Claude Code `2.1.317 (Claude Code)`; models used: with_skill=claude-haiku-5-5, claude-opus-5-5; without_skill=claude-haiku-5-5, claude-opus-5-5

| Arm | Objective | Judge overall | Cost (USD) | Turns | Duration (ms) | Error |
| --- | --- | --- | --- | --- | --- | --- |
| with_skill | 10/10 | skipped (objective-decided) | 0.4489 | 9 | 70529 |  |
| without_skill | 7/10 | skipped (objective-decided) | 0.3689 | 9 | 94824 |  |
