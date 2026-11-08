# Eval report: post-failure-comment

- Prompt: Make CI failures in these workflows self-report to the PR the way the platform's failure-comment action expects.
- Timestamp: 20261108T164040Z
- Run: billing subscription, runner routine, location cloud, id 20261108T163543Z-1d9b73; started 2026-11-08T16:40:40Z, ended 2026-11-08T16:42:06Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.81 to 0.81, from 4 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.37 over 4 call(s); agent $0.29, judge $0.08, guard $0.00; last agent call $0.13
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | Objective | Judge overall | Cost (USD) | Turns | Duration (ms) | Error |
| --- | --- | --- | --- | --- | --- | --- |
| with_skill | 9/12 | 4.3 | 0.1613 | 7 | 26703 |  |
| without_skill | 9/12 | 5.0 | 0.1310 | 9 | 36983 |  |
