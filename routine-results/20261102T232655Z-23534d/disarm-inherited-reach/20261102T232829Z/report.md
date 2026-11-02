# Eval report: disarm-inherited-reach

- Prompt: I want to run a destructive test of `scripts/reaper.sh` against a throwaway copy of `checkout/`. Set that up so nothing can reach the real repo, then run it.
- Timestamp: 20261102T232829Z
- Run: billing subscription, runner routine, location cloud, id 20261102T232655Z-23534d; started 2026-11-02T23:28:29Z, ended 2026-11-02T23:29:49Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.24 to 0.24, from 2 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.28 over 2 call(s); agent $0.28, judge $0.00, guard $0.00; last agent call $0.10
- Harness: Claude Code `2.1.316 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | Objective | Judge overall | Cost (USD) | Turns | Duration (ms) | Error |
| --- | --- | --- | --- | --- | --- | --- |
| with_skill | 7/9 | skipped (objective-decided) | 0.1790 | 9 | 39229 |  |
| without_skill | 6/9 | skipped (objective-decided) | 0.1033 | 7 | 31250 |  |
