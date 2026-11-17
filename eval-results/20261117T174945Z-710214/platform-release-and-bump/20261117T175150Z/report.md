# Eval report: platform-release-and-bump

- Prompt: Bump this consumer to platform v0.1.104.
- Timestamp: 20261117T175150Z
- Run: billing subscription, runner routine, location cloud, id 20261117T174945Z-710214; started 2026-11-17T17:51:50Z, ended 2026-11-17T17:54:26Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.12 to 0.12, from 4 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $1.18 over 4 call(s); agent $0.91, judge $0.27, guard $0.00; last agent call $0.39
- Harness: Claude Code `2.1.326 (Claude Code)`; models used: with_skill=claude-opus-5-5; without_skill=claude-opus-5-5

| Arm | Objective | Judge overall | Cost (USD) | Turns | Duration (ms) | Error |
| --- | --- | --- | --- | --- | --- | --- |
| with_skill | 8/10 | 5.1 | 0.5252 | 12 | 59602 |  |
| without_skill | 8/10 | 5.1 | 0.3866 | 11 | 59580 |  |
