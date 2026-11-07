# Eval report: post-failure-comment

- Prompt: Make CI failures in these workflows self-report to the PR the way the platform's failure-comment action expects.
- Timestamp: 20261107T053138Z
- Run: billing subscription, runner routine, location cloud, id 20261107T053018Z-07d93b; started 2026-11-07T05:31:38Z, ended 2026-11-07T05:33:04Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.34 to 0.34, from 4 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.41 over 4 call(s); agent $0.31, judge $0.10, guard $0.00; last agent call $0.12
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | Objective | Judge overall | Cost (USD) | Turns | Duration (ms) | Error |
| --- | --- | --- | --- | --- | --- | --- |
| with_skill | 9/12 | 5.4 | 0.1922 | 9 | 37609 |  |
| without_skill | 9/12 | 5.1 | 0.1189 | 5 | 25828 |  |
