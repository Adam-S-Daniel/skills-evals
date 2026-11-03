# Eval report: code-quality

- Prompt: Add Go to our lint setup following the house conventions.
- Timestamp: 20261103T080441Z
- Run: billing subscription, runner routine, location cloud, id 20261103T080227Z-a4e443; started 2026-11-03T08:04:41Z, ended 2026-11-03T08:10:41Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.36 to 0.36, from 4 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $2.66 over 4 call(s); agent $1.40, judge $1.27, guard $0.00; last agent call $0.61
- Harness: Claude Code `2.1.317 (Claude Code)`; models used: with_skill=claude-opus-5-5, claude-sonnet-5-5; without_skill=claude-opus-5-5, claude-sonnet-5-5

| Arm | Objective | Judge overall | Cost (USD) | Turns | Duration (ms) | Error |
| --- | --- | --- | --- | --- | --- | --- |
| with_skill | 7/10 | 6.8 | 0.7855 | 11 | 162112 |  |
| without_skill | 7/10 | 5.6 | 0.6131 | 10 | 118361 |  |
