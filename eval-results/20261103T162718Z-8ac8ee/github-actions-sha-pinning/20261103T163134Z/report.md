# Eval report: github-actions-sha-pinning

- Prompt: Bring this repo's action pins into line with the pinning policy.
- Timestamp: 20261103T163134Z
- Run: billing subscription, runner routine, location cloud, id 20261103T162718Z-8ac8ee; started 2026-11-03T16:31:34Z, ended 2026-11-03T16:33:56Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.57 to 0.58, from 5 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $1.06 over 4 call(s); agent $0.72, judge $0.34, guard $0.00; last agent call $0.27
- Harness: Claude Code `2.1.317 (Claude Code)`; models used: with_skill=claude-haiku-5-5, claude-opus-5-5; without_skill=claude-haiku-5-5, claude-opus-5-5

| Arm | Objective | Judge overall | Cost (USD) | Turns | Duration (ms) | Error |
| --- | --- | --- | --- | --- | --- | --- |
| with_skill | 10/10 | 9.7 | 0.4500 | 8 | 64741 |  |
| without_skill | 10/10 | 9.7 | 0.2731 | 6 | 54794 |  |
