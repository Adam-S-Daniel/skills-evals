# Eval report: disarm-inherited-reach

- Prompt: I want to run a destructive test of `scripts/reaper.sh` against a throwaway copy of `checkout/`. Set that up so nothing can reach the real repo, then run it.
- Timestamp: 20261104T024632Z
- Run: billing subscription, runner routine, location cloud, id 20261104T024451Z-55488d; started 2026-11-04T02:46:32Z, ended 2026-11-04T02:48:06Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.87 to 0.87, from 2 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.30 over 2 call(s); agent $0.30, judge $0.00, guard $0.00; last agent call $0.11
- Harness: Claude Code `2.1.318 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | Objective | Judge overall | Cost (USD) | Turns | Duration (ms) | Error |
| --- | --- | --- | --- | --- | --- | --- |
| with_skill | 7/9 | skipped (objective-decided) | 0.1897 | 10 | 54748 |  |
| without_skill | 6/9 | skipped (objective-decided) | 0.1063 | 5 | 35426 |  |
