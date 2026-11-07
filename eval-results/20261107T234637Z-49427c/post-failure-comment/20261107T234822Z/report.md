# Eval report: post-failure-comment

- Prompt: Make CI failures in these workflows self-report to the PR the way the platform's failure-comment action expects.
- Timestamp: 20261107T234822Z
- Run: billing subscription, runner routine, location cloud, id 20261107T234637Z-49427c; started 2026-11-07T23:48:22Z, ended 2026-11-07T23:51:47Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.7 to 0.7, from 4 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $1.19 over 4 call(s); agent $0.88, judge $0.31, guard $0.00; last agent call $0.37
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-haiku-5-5, claude-opus-5-5; without_skill=claude-haiku-5-5, claude-opus-5-5

| Arm | Objective | Judge overall | Cost (USD) | Turns | Duration (ms) | Error |
| --- | --- | --- | --- | --- | --- | --- |
| with_skill | 9/12 | 6.1 | 0.5095 | 8 | 87562 |  |
| without_skill | 9/12 | 5.5 | 0.3704 | 7 | 79507 |  |
