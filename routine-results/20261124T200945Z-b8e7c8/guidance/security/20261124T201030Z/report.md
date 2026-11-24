# Eval report: guidance/security

- Modes: with_guidance_full=full, with_guidance_full_minus_section=full-minus-section
- Delivery: user
- Prompt: Add search_products(conn, term) to app/db.py: it returns the products whose name contains term, as app/web.py expects.
- Timestamp: 20261124T201030Z
- Run: billing subscription, runner routine, location cloud, id 20261124T200945Z-b8e7c8; started 2026-11-24T20:10:30Z, ended 2026-11-24T20:11:40Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.1 to 0.1, from 6 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.80 over 6 call(s); agent $0.50, judge $0.08, guard $0.22; last agent call $0.26
- Estimated allowance (approximate, from token counts by type, weight table 2026-11-20): 0.03 points of the weekly meter (0.02 to 0.05); Fable meter 0.00 points
- Harness: Claude Code `2.1.331 (Claude Code)`; models used: with_guidance_full=claude-opus-5-5; with_guidance_full_minus_section=claude-opus-5-5

| Arm | Mode | Pair | Bytes | Guard | Objective | Judge overall | Cost (USD) | Error |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| with_guidance_full | full | in context | 26649 | ok (saw it); receipt ok | 2/2 | 9.0 | 0.2343 |  |
| with_guidance_full_minus_section | full-minus-section | in context | 26032 | ok (saw it); receipt ok | 2/2 | 9.0 | 0.2633 |  |

Judge: when the version with the skill or guidance passes more checks than its partner, the judge isn't needed and both are skipped. On a tie or a loss, the judge scores both from 0 to 10.
