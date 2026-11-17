# Eval report: platform-release-and-bump

- Prompt: Bump this consumer to platform v0.1.104.
- Timestamp: 20261117T184816Z
- Run: billing subscription, runner routine, location cloud, id 20261117T184510Z-bdc314; started 2026-11-17T18:48:16Z, ended 2026-11-17T18:50:49Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.13 to 0.13, from 4 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $1.18 over 4 call(s); agent $0.90, judge $0.28, guard $0.00; last agent call $0.32
- Harness: Claude Code `2.1.326 (Claude Code)`; models used: with_skill=claude-opus-5-5; without_skill=claude-opus-5-5

| Arm | Objective | Judge overall | Cost (USD) | Turns | Duration (ms) | Error |
| --- | --- | --- | --- | --- | --- | --- |
| with_skill | 8/10 | 5.6 | 0.5722 | 13 | 68734 |  |
| without_skill | 8/10 | 5.3 | 0.3250 | 9 | 45806 |  |
