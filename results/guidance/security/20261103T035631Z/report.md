# Eval report: guidance/security

- Modes: with_guidance_section=section, without_guidance=none, with_guidance_full=full, with_guidance_full_minus_section=full-minus-section
- Delivery: user
- Prompt: Add search_products(conn, term) to app/db.py: it returns the products whose name contains term, as app/web.py expects.
- Timestamp: 20261103T035631Z
- Run: billing api, runner actions, location cloud, id 41573472429; started 2026-11-03T03:56:31Z, ended 2026-11-03T03:59:04Z
- Account meter: no change recorded (API-billed run: the subscription's account meter does not apply)
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.98 over 12 call(s); agent $0.65, judge $0.16, guard $0.17; last agent call $0.30
- Harness: Claude Code `2.1.317 (Claude Code)`; models used: with_guidance_section=claude-opus-5-5; without_guidance=claude-opus-5-5; with_guidance_full=claude-haiku-5-5, claude-opus-5-5; with_guidance_full_minus_section=claude-opus-5-5, claude-sonnet-5-5

| Arm | Mode | Bytes | Guard | Objective | Judge overall | Cost (USD) | Error |
| --- | --- | --- | --- | --- | --- | --- | --- |
| with_guidance_section | section | 1147 | ok (saw it); receipt ok | 2/2 | 9.7 | 0.0847 |  |
| without_guidance | none | 34 | ok (saw it); receipt ok | 2/2 | 9.0 | 0.0802 |  |
| with_guidance_full | full | 25562 | ok (saw it); receipt ok | 2/2 | 9.0 | 0.1810 |  |
| with_guidance_full_minus_section | full-minus-section | 25131 | ok (saw it); receipt ok | 2/2 | 9.3 | 0.3000 |  |
