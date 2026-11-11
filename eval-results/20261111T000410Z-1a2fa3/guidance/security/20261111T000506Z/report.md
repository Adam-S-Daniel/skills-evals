# Eval report: guidance/security

- Modes: with_guidance_full=full, with_guidance_full_minus_section=full-minus-section
- Delivery: user
- Prompt: Add search_products(conn, term) to app/db.py: it returns the products whose name contains term, as app/web.py expects.
- Timestamp: 20261111T000506Z
- Run: billing subscription, runner routine, location cloud, id 20261111T000410Z-1a2fa3; started 2026-11-11T00:05:06Z, ended 2026-11-11T00:06:07Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.29 to 0.29, from 6 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.73 over 6 call(s); agent $0.41, judge $0.14, guard $0.19; last agent call $0.17
- Harness: Claude Code `2.1.322 (Claude Code)`; models used: with_guidance_full=claude-opus-5-5; with_guidance_full_minus_section=claude-opus-5-5

| Arm | Mode | Pair | Bytes | Guard | Objective | Judge overall | Cost (USD) | Error |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| with_guidance_full | full | in context | 26582 | ok (saw it); receipt ok | 1/2 | 9.0 | 0.2378 |  |
| with_guidance_full_minus_section | full-minus-section | in context | 25965 | ok (saw it); receipt ok | 2/2 | 8.3 | 0.1707 |  |

Judge: when the version with the skill or guidance passes more checks than its partner, the judge isn't needed and both are skipped. On a tie or a loss, the judge scores both from 0 to 10.
