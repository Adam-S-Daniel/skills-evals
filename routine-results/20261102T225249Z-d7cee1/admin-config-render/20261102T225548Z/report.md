# Eval report: admin-config-render

- Prompt: /admin shows only the built-in collections and none of ours. Fix it.
- Timestamp: 20261102T225548Z
- Run: billing subscription, runner routine, location cloud, id 20261102T225249Z-d7cee1; started 2026-11-02T22:55:48Z, ended 2026-11-02T22:56:55Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.22 to 0.22, from 4 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.59 over 4 call(s); agent $0.44, judge $0.15, guard $0.00; last agent call $0.18
- Harness: Claude Code `2.1.316 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | Objective | Judge overall | Cost (USD) | Turns | Duration (ms) | Error |
| --- | --- | --- | --- | --- | --- | --- |
| with_skill | 7/7 | 8.1 | 0.2605 | 10 | 26623 |  |
| without_skill | 7/7 | 9.1 | 0.1822 | 7 | 21684 |  |
