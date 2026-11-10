# Eval report: embeddable-tool-pages

- Prompt: Publish seed/new-tool as a Tools page at /tools/unit-converter/ and embed it in the post _posts/2026-01-01-example.md below the intro.
- Timestamp: 20261110T031548Z
- Run: billing subscription, runner routine, location cloud, id 20261110T031334Z-662437; started 2026-11-10T03:15:48Z, ended 2026-11-10T03:17:18Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.15 to 0.15, from 2 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.51 over 2 call(s); agent $0.51, judge $0.00, guard $0.00; last agent call $0.23
- Harness: Claude Code `2.1.322 (Claude Code)`; models used: with_skill=claude-opus-5-5; without_skill=claude-haiku-5-5, claude-opus-5-5

| Arm | Objective | Judge overall | Cost (USD) | Turns | Duration (ms) | Error |
| --- | --- | --- | --- | --- | --- | --- |
| with_skill | 7/7 | skipped: the version with the skill passed more checks (7 of 7 vs 6 of 7) | 0.2721 | 9 | 35261 |  |
| without_skill | 6/7 | skipped: the version with the skill passed more checks (7 of 7 vs 6 of 7) | 0.2341 | 8 | 50897 |  |

Judge: when the version with the skill or guidance passes more checks than its partner, the judge isn't needed and both are skipped. On a tie or a loss, the judge scores both from 0 to 10.
