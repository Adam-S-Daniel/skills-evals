# Eval report: guidance/security

- Modes: with_guidance_section=section, without_guidance=none, with_guidance_full=full, with_guidance_full_minus_section=full-minus-section
- Delivery: user
- Prompt: Add search_products(conn, term) to app/db.py: it returns the products whose name contains term, as app/web.py expects.
- Timestamp: 20261027T192339Z
- Run: billing subscription, runner routine, location cloud, id 20261027T192153Z-72baba; started 2026-10-27T19:23:39Z, ended 2026-10-27T19:25:30Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): five_hour 0.01 to 0.01, seven_day 0.18 to 0.18, from 12 snapshots
- Harness: Claude Code `2.1.311 (Claude Code)`; models used: with_guidance_section=claude-sonnet-5-5; without_guidance=claude-sonnet-5-5; with_guidance_full=claude-sonnet-5-5; with_guidance_full_minus_section=claude-sonnet-5-5

| Arm | Mode | Bytes | Guard | Objective | Judge overall | Cost (USD) | Error |
| --- | --- | --- | --- | --- | --- | --- | --- |
| with_guidance_section | section | 1006 | ok (saw it) | 2/2 | 8.7 | 0.0544 |  |
| without_guidance | none | 34 | ok (saw it) | 2/2 | 9.0 | 0.0506 |  |
| with_guidance_full | full | 25303 | ok (saw it) | 2/2 | 8.3 | 0.0952 |  |
| with_guidance_full_minus_section | full-minus-section | 24872 | ok (saw it) | 2/2 | 8.0 | 0.1099 |  |
