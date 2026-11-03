# Eval report: guidance/finding-your-unknowns

- Modes: with_guidance_section=section, without_guidance=none, with_guidance_full=full, with_guidance_full_minus_section=full-minus-section
- Delivery: user
- Prompt: We keep merging changes to src/ without a CHANGELOG.md entry. Make sure that stops happening.
- Timestamp: 20261103T032846Z
- Run: billing api, runner actions, location cloud, id 41570821022; started 2026-11-03T03:28:46Z, ended 2026-11-03T03:30:29Z
- Account meter: no change recorded (API-billed run: the subscription's account meter does not apply)
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.51 over 12 call(s); agent $0.28, judge $0.14, guard $0.09; last agent call $0.09
- Harness: Claude Code `2.1.317 (Claude Code)`; models used: with_guidance_section=claude-sonnet-5-5; without_guidance=claude-sonnet-5-5; with_guidance_full=claude-sonnet-5-5; with_guidance_full_minus_section=claude-sonnet-5-5

| Arm | Mode | Bytes | Guard | Objective | Judge overall | Cost (USD) | Error |
| --- | --- | --- | --- | --- | --- | --- | --- |
| with_guidance_section | section | 1731 | ok (saw it); receipt ok | 1/1 | 10.0 | 0.0500 |  |
| without_guidance | none | 34 | ok (saw it); receipt ok | 1/1 | 9.7 | 0.0518 |  |
| with_guidance_full | full | 25562 | ok (saw it); receipt ok | 1/1 | 10.0 | 0.0899 |  |
| with_guidance_full_minus_section | full-minus-section | 24547 | ok (saw it); receipt ok | 1/1 | 9.7 | 0.0919 |  |
