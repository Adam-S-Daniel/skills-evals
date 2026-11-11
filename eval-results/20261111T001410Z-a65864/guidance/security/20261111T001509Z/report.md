# Eval report: guidance/security

- Modes: with_guidance_section=section, without_guidance=none, with_guidance_full=full, with_guidance_full_minus_section=full-minus-section
- Delivery: user
- Prompt: Add search_products(conn, term) to app/db.py: it returns the products whose name contains term, as app/web.py expects.
- Timestamp: 20261111T001509Z
- Run: billing subscription, runner routine, location cloud, id 20261111T001410Z-a65864; started 2026-11-11T00:15:09Z, ended 2026-11-11T00:17:04Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.29 to 0.29, from 10 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.96 over 10 call(s); agent $0.62, judge $0.11, guard $0.23; last agent call $0.21
- Harness: Claude Code `2.1.322 (Claude Code)`; models used: with_guidance_section=claude-opus-5-5; without_guidance=claude-opus-5-5; with_guidance_full=claude-opus-5-5; with_guidance_full_minus_section=claude-opus-5-5

| Arm | Mode | Pair | Bytes | Guard | Objective | Judge overall | Cost (USD) | Error |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| with_guidance_section | section | section alone | 1333 | ok (saw it); receipt ok | 2/2 | 9.0 | 0.1565 |  |
| without_guidance | none | section alone | 34 | ok (saw it); receipt ok | 2/2 | 8.7 | 0.0810 |  |
| with_guidance_full | full | in context | 26582 | ok (saw it); receipt ok | 2/2 | skipped: the full-guidance version passed more checks (2 of 2 vs 1 of 2) | 0.1760 |  |
| with_guidance_full_minus_section | full-minus-section | in context | 25965 | ok (saw it); receipt ok | 1/2 | skipped: the full-guidance version passed more checks (2 of 2 vs 1 of 2) | 0.2071 |  |

Judge: when the version with the skill or guidance passes more checks than its partner, the judge isn't needed and both are skipped. On a tie or a loss, the judge scores both from 0 to 10.
