# Eval report: post-failure-comment

- Prompt: Make CI failures in these workflows self-report to the PR the way the platform's failure-comment action expects.
- Timestamp: 20261107T073456Z
- Run: billing subscription, runner routine, location cloud, id 20261107T073325Z-36131e; started 2026-11-07T07:34:56Z, ended 2026-11-07T07:36:29Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.35 to 0.35, from 4 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.42 over 4 call(s); agent $0.31, judge $0.10, guard $0.00; last agent call $0.13
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | Objective | Judge overall | Cost (USD) | Turns | Duration (ms) | Error |
| --- | --- | --- | --- | --- | --- | --- |
| with_skill | 9/12 | 5.0 | 0.1816 | 8 | 25464 |  |
| without_skill | 9/12 | 5.1 | 0.1319 | 6 | 41512 |  |
