# Eval report: post-failure-comment

- Prompt: Make CI failures in these workflows self-report to the PR the way the platform's failure-comment action expects.
- Timestamp: 20261108T011612Z
- Run: billing subscription, runner routine, location cloud, id 20261108T011437Z-b3fbe2; started 2026-11-08T01:16:12Z, ended 2026-11-08T01:20:15Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.71 to 0.71, from 2 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $1.17 over 2 call(s); agent $1.17, judge $0.00, guard $0.00; last agent call $0.63
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-haiku-5-5, claude-opus-5-5; without_skill=claude-haiku-5-5, claude-opus-5-5

| Arm | Objective | Judge overall | Cost (USD) | Turns | Duration (ms) | Error |
| --- | --- | --- | --- | --- | --- | --- |
| with_skill | 9/12 | skipped (objective-decided) | 0.5419 | 9 | 104381 |  |
| without_skill | 8/12 | skipped (objective-decided) | 0.6284 | 10 | 133503 |  |
