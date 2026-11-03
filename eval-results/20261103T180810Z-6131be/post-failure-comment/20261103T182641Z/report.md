# Eval report: post-failure-comment

- Prompt: Make CI failures in these workflows self-report to the PR the way the platform's failure-comment action expects.
- Timestamp: 20261103T182641Z
- Run: billing subscription, runner routine, location cloud, id 20261103T180810Z-6131be; started 2026-11-03T18:26:41Z, ended 2026-11-03T18:30:01Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.65 to 0.65, from 4 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $1.35 over 4 call(s); agent $0.85, judge $0.50, guard $0.00; last agent call $0.40
- Harness: Claude Code `2.1.317 (Claude Code)`; models used: with_skill=claude-opus-5-5; without_skill=claude-haiku-5-5, claude-opus-5-5

| Arm | Objective | Judge overall | Cost (USD) | Turns | Duration (ms) | Error |
| --- | --- | --- | --- | --- | --- | --- |
| with_skill | 9/12 | 6.0 | 0.4511 | 8 | 61562 |  |
| without_skill | 9/12 | 6.5 | 0.4009 | 7 | 95132 |  |
