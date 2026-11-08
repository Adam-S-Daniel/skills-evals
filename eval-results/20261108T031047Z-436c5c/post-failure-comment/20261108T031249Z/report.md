# Eval report: post-failure-comment

- Prompt: Make CI failures in these workflows self-report to the PR the way the platform's failure-comment action expects.
- Timestamp: 20261108T031249Z
- Run: billing subscription, runner routine, location cloud, id 20261108T031047Z-436c5c; started 2026-11-08T03:12:49Z, ended 2026-11-08T03:16:26Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.72 to 0.72, from 2 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $1.16 over 2 call(s); agent $1.16, judge $0.00, guard $0.00; last agent call $0.60
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-haiku-5-5, claude-opus-5-5; without_skill=claude-haiku-5-5, claude-opus-5-5

| Arm | Objective | Judge overall | Cost (USD) | Turns | Duration (ms) | Error |
| --- | --- | --- | --- | --- | --- | --- |
| with_skill | 9/12 | skipped (objective-decided) | 0.5608 | 10 | 101474 |  |
| without_skill | 8/12 | skipped (objective-decided) | 0.5951 | 9 | 111131 |  |
