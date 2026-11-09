# Eval report: guidance/finding-your-unknowns

- Modes: with_guidance_section=section, without_guidance=none, with_guidance_full=full, with_guidance_full_minus_section=full-minus-section
- Delivery: user
- Prompt: We keep merging changes to src/ without a CHANGELOG.md entry. Make sure that stops happening.
- Timestamp: 20261109T211509Z
- Run: billing api, runner actions, location cloud, id 42696732947; started 2026-11-09T21:15:09Z, ended 2026-11-09T21:17:41Z
- Account meter: no change recorded (API-billed run: the subscription's account meter does not apply)
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.91 over 12 call(s); agent $0.66, judge $0.07, guard $0.18; last agent call $0.22
- Harness: Claude Code `2.1.321 (Claude Code)`; models used: with_guidance_section=claude-opus-5-5; without_guidance=claude-opus-5-5; with_guidance_full=claude-opus-5-5; with_guidance_full_minus_section=claude-opus-5-5

| Arm | Mode | Bytes | Guard | Objective | Judge overall | Cost (USD) | Error |
| --- | --- | --- | --- | --- | --- | --- | --- |
| with_guidance_section | section | 1731 | ok (saw it); receipt ok | 1/1 | 9.7 | 0.1238 |  |
| without_guidance | none | 34 | ok (saw it); receipt ok | 1/1 | 9.7 | 0.1104 |  |
| with_guidance_full | full | 26582 | ok (saw it); receipt ok | 1/1 | 10.0 | 0.2084 |  |
| with_guidance_full_minus_section | full-minus-section | 25567 | ok (saw it); receipt ok | 1/1 | 9.7 | 0.2201 |  |
