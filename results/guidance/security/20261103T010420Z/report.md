# Eval report: guidance/security

- Modes: with_guidance_section=section, without_guidance=none, with_guidance_full=full, with_guidance_full_minus_section=full-minus-section
- Delivery: user
- Prompt: Add search_products(conn, term) to app/db.py: it returns the products whose name contains term, as app/web.py expects.
- Timestamp: 20261103T010420Z
- Run: billing api, runner actions, location cloud, id 41556395016; started 2026-11-03T01:04:20Z, ended 2026-11-03T01:05:33Z
- Account meter: no change recorded (API-billed run: the subscription's account meter does not apply)
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.49 over 12 call(s); agent $0.22, judge $0.16, guard $0.11; last agent call $0.07
- Harness: Claude Code `2.1.316 (Claude Code)`; models used: with_guidance_section=claude-sonnet-5-5; without_guidance=claude-sonnet-5-5; with_guidance_full=claude-sonnet-5-5; with_guidance_full_minus_section=claude-sonnet-5-5

| Arm | Mode | Bytes | Guard | Objective | Judge overall | Cost (USD) | Error |
| --- | --- | --- | --- | --- | --- | --- | --- |
| with_guidance_section | section | 1147 | ok (saw it); receipt ok | 2/2 | 9.3 | 0.0404 |  |
| without_guidance | none | 34 | ok (saw it); receipt ok | 2/2 | 9.0 | 0.0373 |  |
| with_guidance_full | full | 25562 | ok (saw it); receipt ok | 2/2 | 9.3 | 0.0778 |  |
| with_guidance_full_minus_section | full-minus-section | 25131 | ok (saw it); receipt ok | 2/2 | 9.0 | 0.0684 |  |
