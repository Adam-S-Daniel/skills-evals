# Eval report: guidance/finding-your-unknowns

- Modes: with_guidance_section=section, without_guidance=none, with_guidance_full=full, with_guidance_full_minus_section=full-minus-section
- Delivery: user
- Prompt: Agents in every one of our repositories keep telling me a CI run passed when all they saw was their watch command finish. Make sure agents across the fleet stop doing that.
- Timestamp: 20261109T211538Z
- Run: billing api, runner actions, location cloud, id 42696732947; started 2026-11-09T21:15:38Z, ended 2026-11-09T21:18:52Z
- Account meter: no change recorded (API-billed run: the subscription's account meter does not apply)
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $1.06 over 12 call(s); agent $0.80, judge $0.08, guard $0.18; last agent call $0.27
- Harness: Claude Code `2.1.321 (Claude Code)`; models used: with_guidance_section=claude-opus-5-5; without_guidance=claude-opus-5-5; with_guidance_full=claude-opus-5-5; with_guidance_full_minus_section=claude-opus-5-5

| Arm | Mode | Bytes | Guard | Objective | Judge overall | Cost (USD) | Error |
| --- | --- | --- | --- | --- | --- | --- | --- |
| with_guidance_section | section | 1731 | ok (saw it); receipt ok | 3/3 | 9.3 | 0.1332 |  |
| without_guidance | none | 34 | ok (saw it); receipt ok | 3/3 | 8.7 | 0.1093 |  |
| with_guidance_full | full | 26582 | ok (saw it); receipt ok | 3/3 | 10.0 | 0.2842 |  |
| with_guidance_full_minus_section | full-minus-section | 25567 | ok (saw it); receipt ok | 3/3 | 9.3 | 0.2722 |  |
