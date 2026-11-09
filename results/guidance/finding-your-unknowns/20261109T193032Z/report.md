# Eval report: guidance/finding-your-unknowns

- Modes: with_guidance_section=section, without_guidance=none, with_guidance_full=full, with_guidance_full_minus_section=full-minus-section
- Delivery: user
- Prompt: Agents in every one of our repositories keep telling me a CI run passed when all they saw was their watch command finish. Make sure agents across the fleet stop doing that.
- Timestamp: 20261109T193032Z
- Run: billing api, runner actions, location cloud, id 42680911395; started 2026-11-09T19:30:32Z, ended 2026-11-09T19:32:14Z
- Account meter: no change recorded (API-billed run: the subscription's account meter does not apply)
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.47 over 12 call(s); agent $0.29, judge $0.09, guard $0.09; last agent call $0.10
- Harness: Claude Code `2.1.321 (Claude Code)`; models used: with_guidance_section=claude-sonnet-5-5; without_guidance=claude-sonnet-5-5; with_guidance_full=claude-sonnet-5-5; with_guidance_full_minus_section=claude-sonnet-5-5

| Arm | Mode | Bytes | Guard | Objective | Judge overall | Cost (USD) | Error |
| --- | --- | --- | --- | --- | --- | --- | --- |
| with_guidance_section | section | 1731 | ok (saw it); receipt ok | 3/3 | 8.3 | 0.0509 |  |
| without_guidance | none | 34 | ok (saw it); receipt ok | 3/3 | 8.0 | 0.0506 |  |
| with_guidance_full | full | 26582 | ok (saw it); receipt ok | 3/3 | 9.7 | 0.0865 |  |
| with_guidance_full_minus_section | full-minus-section | 25567 | ok (saw it); receipt ok | 3/3 | 9.0 | 0.0997 |  |
