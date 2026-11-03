# Eval report: disarm-inherited-reach

- Prompt: I want to run a destructive test of `scripts/reaper.sh` against a throwaway copy of `checkout/`. Set that up so nothing can reach the real repo, then run it.
- Timestamp: 20261103T061548Z
- Run: billing subscription, runner routine, location cloud, id 20261103T061404Z-cc89bf; started 2026-11-03T06:15:48Z, ended 2026-11-03T06:17:49Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.34 to 0.34, from 2 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.75 over 2 call(s); agent $0.75, judge $0.00, guard $0.00; last agent call $0.25
- Harness: Claude Code `2.1.317 (Claude Code)`; models used: with_skill=claude-opus-5-5; without_skill=claude-opus-5-5

| Arm | Objective | Judge overall | Cost (USD) | Turns | Duration (ms) | Error |
| --- | --- | --- | --- | --- | --- | --- |
| with_skill | 9/9 | skipped (objective-decided) | 0.5016 | 9 | 61108 |  |
| without_skill | 6/9 | skipped (objective-decided) | 0.2509 | 6 | 53952 |  |
