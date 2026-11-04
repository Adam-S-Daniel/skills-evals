# Eval report: github-actions-sha-pinning

- Prompt: Bring this repo's action pins into line with the pinning policy.
- Timestamp: 20261104T010518Z
- Run: billing subscription, runner routine, location cloud, id 20261104T010336Z-243e7f; started 2026-11-04T01:05:18Z, ended 2026-11-04T01:08:14Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.84 to 0.84, from 2 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.85 over 2 call(s); agent $0.85, judge $0.00, guard $0.00; last agent call $0.41
- Harness: Claude Code `2.1.318 (Claude Code)`; models used: with_skill=claude-haiku-5-5, claude-opus-5-5; without_skill=claude-haiku-5-5, claude-opus-5-5

| Arm | Objective | Judge overall | Cost (USD) | Turns | Duration (ms) | Error |
| --- | --- | --- | --- | --- | --- | --- |
| with_skill | 8/10 | skipped (objective-decided) | 0.4373 | 8 | 57384 |  |
| without_skill | 7/10 | skipped (objective-decided) | 0.4084 | 9 | 112958 |  |
