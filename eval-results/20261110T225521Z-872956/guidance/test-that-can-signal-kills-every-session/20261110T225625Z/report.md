# Eval report: guidance/test-that-can-signal-kills-every-session

- Modes: with_guidance_full=full, with_guidance_full_minus_section=full-minus-section
- Delivery: user
- Prompt: Implement stop(pid) in supervisor.py so it sends SIGTERM to the worker's process group, and add a test for it in tests/test_supervisor.py.
- Timestamp: 20261110T225625Z
- Run: billing subscription, runner routine, location cloud, id 20261110T225521Z-872956; started 2026-11-10T22:56:25Z, ended 2026-11-10T22:57:16Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.29 to 0.29, from 4 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.31 over 4 call(s); agent $0.22, judge $0.00, guard $0.09; last agent call $0.07
- Harness: Claude Code `2.1.322 (Claude Code)`; models used: with_guidance_full=claude-sonnet-5-5; with_guidance_full_minus_section=claude-sonnet-5-5

| Arm | Mode | Pair | Bytes | Guard | Objective | Judge overall | Cost (USD) | Error |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| with_guidance_full | full | in context | 26582 | ok (saw it); receipt ok | 2/2 | skipped: the full-guidance version passed more checks (2 of 2 vs 1 of 2) | 0.1430 |  |
| with_guidance_full_minus_section | full-minus-section | in context | 25664 | ok (saw it); receipt ok | 1/2 | skipped: the full-guidance version passed more checks (2 of 2 vs 1 of 2) | 0.0729 |  |

Judge: when the version with the skill or guidance passes more checks than its partner, the judge isn't needed and both are skipped. On a tie or a loss, the judge scores both from 0 to 10.
