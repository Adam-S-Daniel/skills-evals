# Eval report: github-actions-sha-pinning

- Prompt: Bring this repo's action pins into line with the pinning policy.
- Timestamp: 20261103T124846Z
- Run: billing subscription, runner routine, location cloud, id 20261103T124650Z-c14e10; started 2026-11-03T12:48:46Z, ended 2026-11-03T12:51:50Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.41 to 0.41, from 4 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $1.16 over 4 call(s); agent $0.79, judge $0.38, guard $0.00; last agent call $0.33
- Harness: Claude Code `2.1.317 (Claude Code)`; models used: with_skill=claude-haiku-5-5, claude-opus-5-5; without_skill=claude-haiku-5-5, claude-opus-5-5

| Arm | Objective | Judge overall | Cost (USD) | Turns | Duration (ms) | Error |
| --- | --- | --- | --- | --- | --- | --- |
| with_skill | 10/10 | 10.0 | 0.4560 | 9 | 67109 |  |
| without_skill | 10/10 | 8.9 | 0.3301 | 6 | 86737 |  |
