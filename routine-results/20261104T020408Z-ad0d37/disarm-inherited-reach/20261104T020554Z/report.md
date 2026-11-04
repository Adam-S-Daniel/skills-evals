# Eval report: disarm-inherited-reach

- Prompt: I want to run a destructive test of `scripts/reaper.sh` against a throwaway copy of `checkout/`. Set that up so nothing can reach the real repo, then run it.
- Timestamp: 20261104T020554Z
- Run: billing subscription, runner routine, location cloud, id 20261104T020408Z-ad0d37; started 2026-11-04T02:05:54Z, ended 2026-11-04T02:08:30Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.85 to 0.85, from 4 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $1.10 over 4 call(s); agent $0.63, judge $0.47, guard $0.00; last agent call $0.23
- Harness: Claude Code `2.1.318 (Claude Code)`; models used: with_skill=claude-opus-5-5; without_skill=claude-opus-5-5

| Arm | Objective | Judge overall | Cost (USD) | Turns | Duration (ms) | Error |
| --- | --- | --- | --- | --- | --- | --- |
| with_skill | 8/9 | 8.7 | 0.3986 | 9 | 60639 |  |
| without_skill | 8/9 | 6.2 | 0.2318 | 6 | 49035 |  |
