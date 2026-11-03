# Eval report: guidance/fleet-spans-two-owners

- Modes: with_guidance_section=section, without_guidance=none, with_guidance_full=full, with_guidance_full_minus_section=full-minus-section
- Delivery: user
- Prompt: Which repositories in the fleet have no skills.lock at their root? Write them to MISSING.md, one owner/name per line and nothing else, and tell me how you checked.
- Timestamp: 20261103T012041Z
- Run: billing api, runner actions, location cloud, id 41557705869; started 2026-11-03T01:20:41Z, ended 2026-11-03T01:22:08Z
- Account meter: no change recorded (API-billed run: the subscription's account meter does not apply)
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.50 over 12 call(s); agent $0.27, judge $0.14, guard $0.09; last agent call $0.09
- Harness: Claude Code `2.1.316 (Claude Code)`; models used: with_guidance_section=claude-sonnet-5-5; without_guidance=claude-sonnet-5-5; with_guidance_full=claude-sonnet-5-5; with_guidance_full_minus_section=claude-sonnet-5-5

| Arm | Mode | Bytes | Guard | Objective | Judge overall | Cost (USD) | Error |
| --- | --- | --- | --- | --- | --- | --- | --- |
| with_guidance_section | section | 1679 | ok (saw it); receipt ok | 2/3 | 9.7 | 0.0490 |  |
| without_guidance | none | 34 | ok (saw it); receipt ok | 3/3 | 10.0 | 0.0507 |  |
| with_guidance_full | full | 25562 | ok (saw it); receipt ok | 3/3 | 10.0 | 0.0838 |  |
| with_guidance_full_minus_section | full-minus-section | 24599 | ok (saw it); receipt ok | 3/3 | 9.3 | 0.0902 |  |
