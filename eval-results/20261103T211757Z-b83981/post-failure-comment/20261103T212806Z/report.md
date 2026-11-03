# Eval report: post-failure-comment

- Prompt: Make CI failures in these workflows self-report to the PR the way the platform's failure-comment action expects.
- Timestamp: 20261103T212806Z
- Run: billing subscription, runner routine, location cloud, id 20261103T211757Z-b83981; started 2026-11-03T21:28:06Z, ended 2026-11-03T21:29:34Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.72 to 0.72, from 4 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.52 over 4 call(s); agent $0.34, judge $0.18, guard $0.00; last agent call $0.15
- Harness: Claude Code `2.1.317 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | Objective | Judge overall | Cost (USD) | Turns | Duration (ms) | Error |
| --- | --- | --- | --- | --- | --- | --- |
| with_skill | 9/12 | 5.0 | 0.1957 | 9 | 30796 |  |
| without_skill | 9/12 | 5.7 | 0.1450 | 8 | 35330 |  |
