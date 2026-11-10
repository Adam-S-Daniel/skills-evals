# Eval report: embeddable-tool-pages

- Prompt: Publish seed/new-tool as a Tools page at /tools/unit-converter/ and embed it in the post _posts/2026-01-01-example.md below the intro.
- Timestamp: 20261110T045156Z
- Run: billing subscription, runner routine, location cloud, id 20261110T044938Z-e51140; started 2026-11-10T04:51:56Z, ended 2026-11-10T04:53:10Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.18 to 0.18, from 2 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.55 over 2 call(s); agent $0.55, judge $0.00, guard $0.00; last agent call $0.23
- Harness: Claude Code `2.1.322 (Claude Code)`; models used: with_skill=claude-opus-5-5; without_skill=claude-opus-5-5

| Arm | Objective | Judge overall | Cost (USD) | Turns | Duration (ms) | Error |
| --- | --- | --- | --- | --- | --- | --- |
| with_skill | 7/7 | skipped: the version with the skill passed more checks (7 of 7 vs 6 of 7) | 0.3235 | 8 | 28289 |  |
| without_skill | 6/7 | skipped: the version with the skill passed more checks (7 of 7 vs 6 of 7) | 0.2289 | 8 | 41659 |  |

Judge: when the version with the skill or guidance passes more checks than its partner, the judge isn't needed and both are skipped. On a tie or a loss, the judge scores both from 0 to 10.
