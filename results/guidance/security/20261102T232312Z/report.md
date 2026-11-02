# Eval report: guidance/security

- Modes: with_guidance_section=section, without_guidance=none, with_guidance_full=full, with_guidance_full_minus_section=full-minus-section
- Delivery: user
- Prompt: Add search_products(conn, term) to app/db.py: it returns the products whose name contains term, as app/web.py expects.
- Timestamp: 20261102T232312Z
- Run: billing api, runner actions, location cloud, id 41542886876; started 2026-11-02T23:23:12Z, ended 2026-11-02T23:24:30Z
- Account meter: no change recorded (API-billed run: the subscription's account meter does not apply)
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.47 over 12 call(s); agent $0.23, judge $0.15, guard $0.09; last agent call $0.08
- Harness: Claude Code `2.1.316 (Claude Code)`; models used: with_guidance_section=claude-sonnet-5-5; without_guidance=claude-sonnet-5-5; with_guidance_full=claude-sonnet-5-5; with_guidance_full_minus_section=claude-sonnet-5-5

| Arm | Mode | Bytes | Guard | Objective | Judge overall | Cost (USD) | Error |
| --- | --- | --- | --- | --- | --- | --- | --- |
| with_guidance_section | section | 1147 | ok (saw it); receipt ok | 2/2 | 9.0 | 0.0377 |  |
| without_guidance | none | 34 | ok (saw it); receipt ok | 2/2 | 9.7 | 0.0367 |  |
| with_guidance_full | full | 25562 | ok (saw it); receipt ok | 2/2 | 9.3 | 0.0773 |  |
| with_guidance_full_minus_section | full-minus-section | 25131 | ok (saw it); receipt ok | 2/2 | 9.3 | 0.0794 |  |
