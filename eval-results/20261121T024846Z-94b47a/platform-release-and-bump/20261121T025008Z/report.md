# Eval report: platform-release-and-bump

- Prompt: Bump this consumer to platform v0.1.104.
- Timestamp: 20261121T025008Z
- Run: billing subscription, runner routine, location cloud, id 20261121T024846Z-94b47a; started 2026-11-21T02:50:08Z, ended 2026-11-21T02:51:25Z
- Budget stop: account_above (limit 0.8, weekly meter 0.83, moved 0.000335); no trial or judge call started after it
- Account meter: no change recorded (fewer than two meter snapshots that share a window were recorded; the meter is read once per call (agent, judge or guard), as the call starts, so a run of one agent call and no other has none)
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.76 over 1 call(s); agent $0.76, judge $0.00, guard $0.00; last agent call $0.76
- Estimated allowance (approximate, from token counts by type, weight table 2026-11-20): 0.03 points of the weekly meter (0.02 to 0.05); Fable meter 0.00 points
- Harness: Claude Code `2.1.330 (Claude Code)`; models used: with_skill=claude-opus-5-5; without_skill=none recorded

| Arm | Objective | Judge overall | Cost (USD) | Turns | Duration (ms) | Error |
| --- | --- | --- | --- | --- | --- | --- |
| with_skill | 8/10 | error | 0.7593 | 13 | 66340 |  |
| without_skill | - | - | - | - | - | budget_stop: trial not started: the run reached its budget stop (account_above); see usage.budget_stop |
