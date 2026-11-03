# Eval report: admin-config-render

- Prompt: /admin shows only the built-in collections and none of ours. Fix it.
- Timestamp: 20261103T024216Z
- Run: billing subscription, runner routine, location cloud, id 20261103T024035Z-4b60ac; started 2026-11-03T02:42:16Z, ended 2026-11-03T02:44:07Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.3 to 0.3, from 4 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $1.97 over 4 call(s); agent $0.98, judge $0.99, guard $0.00; last agent call $0.42
- Harness: Claude Code `2.1.317 (Claude Code)`; models used: with_skill=claude-opus-5-5; without_skill=claude-opus-5-5

| Arm | Objective | Judge overall | Cost (USD) | Turns | Duration (ms) | Error |
| --- | --- | --- | --- | --- | --- | --- |
| with_skill | 7/7 | 9.1 | 0.5534 | 9 | 32356 |  |
| without_skill | 7/7 | 8.7 | 0.4247 | 8 | 42071 |  |
