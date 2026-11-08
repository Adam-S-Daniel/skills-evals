# Eval report: post-failure-comment

- Prompt: Make CI failures in these workflows self-report to the PR the way the platform's failure-comment action expects.
- Timestamp: 20261108T163718Z
- Run: billing subscription, runner routine, location cloud, id 20261108T163543Z-1d9b73; started 2026-11-08T16:37:18Z, ended 2026-11-08T16:40:39Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.81 to 0.81, from 4 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $1.07 over 4 call(s); agent $0.80, judge $0.27, guard $0.00; last agent call $0.33
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-opus-5-5, claude-sonnet-5-5; without_skill=claude-haiku-5-5, claude-opus-5-5

| Arm | Objective | Judge overall | Cost (USD) | Turns | Duration (ms) | Error |
| --- | --- | --- | --- | --- | --- | --- |
| with_skill | 9/12 | 6.3 | 0.4605 | 8 | 62330 |  |
| without_skill | 9/12 | 5.5 | 0.3349 | 7 | 92445 |  |
