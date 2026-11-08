# Eval report: post-failure-comment

- Prompt: Make CI failures in these workflows self-report to the PR the way the platform's failure-comment action expects.
- Timestamp: 20261108T154327Z
- Run: billing subscription, runner routine, location cloud, id 20261108T154132Z-2dfe70; started 2026-11-08T15:43:27Z, ended 2026-11-08T15:46:54Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.8 to 0.8, from 4 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $1.03 over 4 call(s); agent $0.77, judge $0.26, guard $0.00; last agent call $0.38
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-haiku-5-5, claude-opus-5-5; without_skill=claude-opus-5-5

| Arm | Objective | Judge overall | Cost (USD) | Turns | Duration (ms) | Error |
| --- | --- | --- | --- | --- | --- | --- |
| with_skill | 9/12 | 5.7 | 0.3884 | 9 | 84097 |  |
| without_skill | 9/12 | 6.1 | 0.3830 | 10 | 75792 |  |
