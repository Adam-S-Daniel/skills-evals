# Eval report: post-failure-comment

- Prompt: Make CI failures in these workflows self-report to the PR the way the platform's failure-comment action expects.
- Timestamp: 20261103T205844Z
- Run: billing subscription, runner routine, location cloud, id 20261103T203704Z-7a61c6; started 2026-11-03T20:58:44Z, ended 2026-11-03T21:04:02Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.71 to 0.71, from 4 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $1.96 over 4 call(s); agent $1.01, judge $0.95, guard $0.00; last agent call $0.51
- Harness: Claude Code `2.1.317 (Claude Code)`; models used: with_skill=claude-haiku-5-5, claude-opus-5-5; without_skill=claude-haiku-5-5, claude-opus-5-5

| Arm | Objective | Judge overall | Cost (USD) | Turns | Duration (ms) | Error |
| --- | --- | --- | --- | --- | --- | --- |
| with_skill | 9/12 | 6.0 | 0.4945 | 9 | 85551 |  |
| without_skill | 9/12 | 6.2 | 0.5118 | 9 | 114674 |  |
