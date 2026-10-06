# Eval report: disarm-inherited-reach

- Prompt: I want to run a destructive test of `scripts/reaper.sh` against a throwaway copy of `checkout/`. Set that up so nothing can reach the real repo, then run it.
- Timestamp: 20261006T141516Z
- Harness: Claude Code `2.1.291 (Claude Code)`; models used: with_skill=claude-sonnet-5; without_skill=claude-sonnet-5

| Arm | Objective | Judge overall | Cost (USD) | Turns | Duration (ms) | Error |
| --- | --- | --- | --- | --- | --- | --- |
| with_skill | 9/9 | 8.0 | 0.1681 | 14 | 51189 |  |
| without_skill | 6/9 | 5.9 | 0.1010 | 6 | 49820 |  |
