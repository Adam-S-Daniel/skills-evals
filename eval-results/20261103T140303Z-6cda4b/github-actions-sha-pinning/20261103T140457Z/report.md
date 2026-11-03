# Eval report: github-actions-sha-pinning

- Prompt: Bring this repo's action pins into line with the pinning policy.
- Timestamp: 20261103T140457Z
- Run: billing subscription, runner routine, location cloud, id 20261103T140303Z-6cda4b; started 2026-11-03T14:04:57Z, ended 2026-11-03T14:08:01Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.45 to 0.46, from 3 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.88 over 2 call(s); agent $0.88, judge $0.00, guard $0.00; last agent call $0.36
- Harness: Claude Code `2.1.317 (Claude Code)`; models used: with_skill=claude-haiku-5-5, claude-opus-5-5; without_skill=claude-haiku-5-5, claude-opus-5-5

| Arm | Objective | Judge overall | Cost (USD) | Turns | Duration (ms) | Error |
| --- | --- | --- | --- | --- | --- | --- |
| with_skill | 10/10 | skipped (objective-decided) | 0.5141 | 10 | 89963 |  |
| without_skill | 7/10 | skipped (objective-decided) | 0.3641 | 9 | 82426 |  |
