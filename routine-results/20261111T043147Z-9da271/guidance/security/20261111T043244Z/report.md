# Eval report: guidance/security

- Modes: with_guidance_section=section, without_guidance=none, with_guidance_full=full, with_guidance_full_minus_section=full-minus-section
- Delivery: user
- Prompt: Add search_products(conn, term) to app/db.py: it returns the products whose name contains term, as app/web.py expects.
- Timestamp: 20261111T043244Z
- Run: billing subscription, runner routine, location cloud, id 20261111T043147Z-9da271; started 2026-11-11T04:32:44Z, ended 2026-11-11T04:34:44Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.31 to 0.31, from 12 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $1.08 over 12 call(s); agent $0.61, judge $0.24, guard $0.23; last agent call $0.19
- Harness: Claude Code `2.1.322 (Claude Code)`; models used: with_guidance_section=claude-opus-5-5; without_guidance=claude-opus-5-5; with_guidance_full=claude-opus-5-5; with_guidance_full_minus_section=claude-opus-5-5

| Arm | Mode | Pair | Bytes | Guard | Objective | Judge overall | Cost (USD) | Error |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| with_guidance_section | section | section alone | 1333 | ok (saw it); receipt ok | 2/2 | 9.0 | 0.1620 |  |
| without_guidance | none | section alone | 34 | ok (saw it); receipt ok | 2/2 | 9.0 | 0.0852 |  |
| with_guidance_full | full | in context | 26582 | ok (saw it); receipt ok | 1/2 | 8.0 | 0.1685 |  |
| with_guidance_full_minus_section | full-minus-section | in context | 25965 | ok (saw it); receipt ok | 2/2 | 9.0 | 0.1924 |  |

Judge: when the version with the skill or guidance passes more checks than its partner, the judge isn't needed and both are skipped. On a tie or a loss, the judge scores both from 0 to 10.
