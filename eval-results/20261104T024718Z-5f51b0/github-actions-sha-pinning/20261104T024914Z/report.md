# Eval report: github-actions-sha-pinning

- Prompt: Bring this repo's action pins into line with the pinning policy.
- Timestamp: 20261104T024914Z
- Run: billing subscription, runner routine, location cloud, id 20261104T024718Z-5f51b0; started 2026-11-04T02:49:14Z, ended 2026-11-04T02:51:27Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.87 to 0.87, from 2 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.70 over 2 call(s); agent $0.70, judge $0.00, guard $0.00; last agent call $0.23
- Harness: Claude Code `2.1.318 (Claude Code)`; models used: with_skill=claude-haiku-5-5, claude-opus-5-5; without_skill=claude-opus-5-5

| Arm | Objective | Judge overall | Cost (USD) | Turns | Duration (ms) | Error |
| --- | --- | --- | --- | --- | --- | --- |
| with_skill | 10/10 | skipped (objective-decided) | 0.4703 | 9 | 76015 |  |
| without_skill | 7/10 | skipped (objective-decided) | 0.2305 | 4 | 51781 |  |
