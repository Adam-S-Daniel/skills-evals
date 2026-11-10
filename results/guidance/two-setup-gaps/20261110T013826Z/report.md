# Eval report: guidance/two-setup-gaps

- Modes: with_guidance_section=section, without_guidance=none, with_guidance_full=full, with_guidance_full_minus_section=full-minus-section
- Delivery: user
- Prompt: This is my own durable laptop, not a cloud session, and I am about to start work on the skills registry. Check that this machine's Claude Code plugin setup is in order and fix what is missing.
- Timestamp: 20261110T013826Z
- Run: billing api, runner actions, location cloud, id 42736977807; started 2026-11-10T01:38:26Z, ended 2026-11-10T01:39:39Z
- Account meter: no change recorded (API-billed run: the subscription's account meter does not apply)
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.41 over 10 call(s); agent $0.27, judge $0.03, guard $0.11; last agent call $0.08
- Harness: Claude Code `2.1.321 (Claude Code)`; models used: with_guidance_section=claude-sonnet-5-5; without_guidance=claude-sonnet-5-5; with_guidance_full=claude-sonnet-5-5; with_guidance_full_minus_section=claude-sonnet-5-5

| Arm | Mode | Pair | Bytes | Guard | Objective | Judge overall | Cost (USD) | Error |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| with_guidance_section | section | section alone | 2686 | ok (saw it); receipt ok | 1/1 | skipped: the section-alone version passed more checks (1 of 1 vs 0 of 1) | 0.0468 |  |
| without_guidance | none | section alone | 34 | ok (saw it); receipt ok | 0/1 | skipped: the section-alone version passed more checks (1 of 1 vs 0 of 1) | 0.0489 |  |
| with_guidance_full | full | in context | 26582 | ok (saw it); receipt ok | 1/1 | 7.0 | 0.0871 |  |
| with_guidance_full_minus_section | full-minus-section | in context | 24612 | ok (saw it); receipt ok | 1/1 | 6.3 | 0.0834 |  |

Judge: when the version with the skill or guidance passes more checks than its partner, the judge isn't needed and both are skipped. On a tie or a loss, the judge scores both from 0 to 10.
