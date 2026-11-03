# Eval report: code-quality

- Prompt: Add Go to our lint setup following the house conventions.
- Timestamp: 20261103T073810Z
- Run: billing subscription, runner routine, location cloud, id 20261103T073627Z-c47a51; started 2026-11-03T07:38:10Z, ended 2026-11-03T07:40:28Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.35 to 0.35, from 4 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.52 over 4 call(s); agent $0.34, judge $0.18, guard $0.00; last agent call $0.17
- Harness: Claude Code `2.1.317 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | Objective | Judge overall | Cost (USD) | Turns | Duration (ms) | Error |
| --- | --- | --- | --- | --- | --- | --- |
| with_skill | 7/10 | 6.0 | 0.1686 | 8 | 38569 |  |
| without_skill | 7/10 | 6.4 | 0.1713 | 7 | 61823 |  |
