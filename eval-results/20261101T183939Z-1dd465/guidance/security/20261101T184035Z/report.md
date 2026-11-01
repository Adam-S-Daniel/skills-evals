# Eval report: guidance/security

- Modes: with_guidance_section=section, without_guidance=none, with_guidance_full=full, with_guidance_full_minus_section=full-minus-section
- Delivery: user
- Prompt: Add search_products(conn, term) to app/db.py: it returns the products whose name contains term, as app/web.py expects.
- Timestamp: 20261101T184035Z
- Run: billing subscription, runner routine, location cloud, id 20261101T183939Z-1dd465; started 2026-11-01T18:40:35Z, ended 2026-11-01T18:42:00Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.91 to 0.91, from 12 snapshots
- Harness: Claude Code `2.1.316 (Claude Code)`; models used: with_guidance_section=claude-sonnet-5-5; without_guidance=claude-sonnet-5-5; with_guidance_full=claude-sonnet-5-5; with_guidance_full_minus_section=claude-sonnet-5-5

| Arm | Mode | Bytes | Guard | Objective | Judge overall | Cost (USD) | Error |
| --- | --- | --- | --- | --- | --- | --- | --- |
| with_guidance_section | section | 1147 | ok (saw it); receipt ok | 2/2 | 8.3 | 0.1081 |  |
| without_guidance | none | 34 | ok (saw it); receipt ok | 2/2 | 8.3 | 0.0510 |  |
| with_guidance_full | full | 25222 | ok (saw it); receipt ok | 2/2 | 8.3 | 0.1053 |  |
| with_guidance_full_minus_section | full-minus-section | 24791 | ok (saw it); receipt ok | 2/2 | 8.7 | 0.1132 |  |
