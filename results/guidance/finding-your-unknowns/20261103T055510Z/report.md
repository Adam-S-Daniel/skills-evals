# Eval report: guidance/finding-your-unknowns

- Modes: with_guidance_section=section, without_guidance=none, with_guidance_full=full, with_guidance_full_minus_section=full-minus-section
- Delivery: user
- Prompt: We keep merging changes to src/ without a CHANGELOG.md entry. Make sure that stops happening.
- Timestamp: 20261103T055510Z
- Run: billing api, runner actions, location cloud, id 41585078142; started 2026-11-03T05:55:10Z, ended 2026-11-03T05:59:00Z
- Account meter: no change recorded (API-billed run: the subscription's account meter does not apply)
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $1.11 over 12 call(s); agent $0.78, judge $0.16, guard $0.17; last agent call $0.31
- Harness: Claude Code `2.1.317 (Claude Code)`; models used: with_guidance_section=claude-opus-5-5; without_guidance=claude-opus-5-5; with_guidance_full=claude-haiku-5-5, claude-opus-5-5; with_guidance_full_minus_section=claude-haiku-5-5, claude-opus-5-5

| Arm | Mode | Bytes | Guard | Objective | Judge overall | Cost (USD) | Error |
| --- | --- | --- | --- | --- | --- | --- | --- |
| with_guidance_section | section | 1731 | ok (saw it); receipt ok | 1/1 | 10.0 | 0.1283 |  |
| without_guidance | none | 34 | ok (saw it); receipt ok | 1/1 | 9.7 | 0.1224 |  |
| with_guidance_full | full | 25562 | ok (saw it); receipt ok | 1/1 | 10.0 | 0.2204 |  |
| with_guidance_full_minus_section | full-minus-section | 24547 | ok (saw it); receipt ok | 1/1 | 10.0 | 0.3124 |  |
