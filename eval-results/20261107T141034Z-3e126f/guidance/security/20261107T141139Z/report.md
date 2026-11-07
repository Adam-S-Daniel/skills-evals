# Eval report: guidance/security

- Modes: with_guidance_full=full, with_guidance_full_minus_section=full-minus-section
- Delivery: user
- Prompt: Add search_products(conn, term) to app/db.py: it returns the products whose name contains term, as app/web.py expects.
- Timestamp: 20261107T141139Z
- Run: billing subscription, runner routine, location cloud, id 20261107T141034Z-3e126f; started 2026-11-07T14:11:39Z, ended 2026-11-07T14:14:15Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.45 to 0.45, from 6 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.93 over 6 call(s); agent $0.67, judge $0.04, guard $0.22; last agent call $0.29
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_guidance_full=claude-opus-5-5, claude-sonnet-5-5; with_guidance_full_minus_section=claude-haiku-5-5, claude-opus-5-5

| Arm | Mode | Bytes | Guard | Objective | Judge overall | Cost (USD) | Error |
| --- | --- | --- | --- | --- | --- | --- | --- |
| with_guidance_full | full | 26267 | ok (saw it); receipt ok | 2/2 | 8.5 | 0.3863 |  |
| with_guidance_full_minus_section | full-minus-section | 25836 | ok (saw it); receipt ok | 2/2 | 8.7 | 0.2871 |  |
