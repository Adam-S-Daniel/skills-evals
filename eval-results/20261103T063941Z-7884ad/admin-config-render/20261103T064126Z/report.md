# Eval report: admin-config-render

- Prompt: /admin shows only the built-in collections and none of ours. Fix it.
- Timestamp: 20261103T064126Z
- Run: billing subscription, runner routine, location cloud, id 20261103T063941Z-7884ad; started 2026-11-03T06:41:26Z, ended 2026-11-03T06:42:45Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.35 to 0.35, from 4 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.54 over 4 call(s); agent $0.40, judge $0.14, guard $0.00; last agent call $0.18
- Harness: Claude Code `2.1.317 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | Objective | Judge overall | Cost (USD) | Turns | Duration (ms) | Error |
| --- | --- | --- | --- | --- | --- | --- |
| with_skill | 7/7 | 8.8 | 0.2162 | 12 | 31333 |  |
| without_skill | 7/7 | 8.4 | 0.1819 | 7 | 29170 |  |
