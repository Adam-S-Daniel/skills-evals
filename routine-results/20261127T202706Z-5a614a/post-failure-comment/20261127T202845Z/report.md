# Eval report: post-failure-comment

- Prompt: Make CI failures in these workflows self-report to the PR the way the platform's failure-comment action expects.
- Timestamp: 20261127T202845Z
- Run: billing subscription, runner routine, location cloud, id 20261127T202706Z-5a614a; started 2026-11-27T20:28:45Z, ended 2026-11-27T20:30:12Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.6 to 0.6, from 4 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.50 over 4 call(s); agent $0.39, judge $0.11, guard $0.00; last agent call $0.14
- Estimated allowance (approximate, from token counts by type, weight table 2026-11-20): 0.03 points of the weekly meter (0.02 to 0.05); Fable meter 0.00 points
- Harness: Claude Code `2.1.332 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | Objective | Judge overall | Cost (USD) | Turns | Duration (ms) | Error |
| --- | --- | --- | --- | --- | --- | --- |
| with_skill | 9/12 | 6.1 | 0.2527 | 9 | 25746 |  |
| without_skill | 9/12 | 5.0 | 0.1386 | 6 | 32168 |  |
