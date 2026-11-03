# Eval report: post-failure-comment

- Prompt: Make CI failures in these workflows self-report to the PR the way the platform's failure-comment action expects.
- Timestamp: 20261103T090626Z
- Run: billing subscription, runner routine, location cloud, id 20261103T090409Z-7cf88e; started 2026-11-03T09:06:26Z, ended 2026-11-03T09:11:33Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.37 to 0.37, from 4 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $2.33 over 4 call(s); agent $1.18, judge $1.15, guard $0.00; last agent call $0.54
- Harness: Claude Code `2.1.317 (Claude Code)`; models used: with_skill=claude-opus-5-5, claude-sonnet-5-5; without_skill=claude-haiku-5-5, claude-opus-5-5

| Arm | Objective | Judge overall | Cost (USD) | Turns | Duration (ms) | Error |
| --- | --- | --- | --- | --- | --- | --- |
| with_skill | 4/12 | 4.4 | 0.6445 | 10 | 80428 |  |
| without_skill | 9/12 | 5.7 | 0.5377 | 9 | 112839 |  |
