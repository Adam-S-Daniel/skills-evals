# Eval report: platform-release-and-bump

- Prompt: Bump this consumer to platform v0.1.104.
- Timestamp: 20261117T211648Z
- Run: billing subscription, runner routine, location cloud, id 20261117T211505Z-984ceb; started 2026-11-17T21:16:47Z, ended 2026-11-17T21:19:07Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.15 to 0.15, from 4 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $1.15 over 4 call(s); agent $0.88, judge $0.28, guard $0.00; last agent call $0.35
- Harness: Claude Code `2.1.326 (Claude Code)`; models used: with_skill=claude-opus-5-5; without_skill=claude-opus-5-5

| Arm | Objective | Judge overall | Cost (USD) | Turns | Duration (ms) | Error |
| --- | --- | --- | --- | --- | --- | --- |
| with_skill | 7/10 | 5.3 | 0.5289 | 13 | 53851 |  |
| without_skill | 8/10 | 5.1 | 0.3472 | 10 | 48274 |  |
