# Eval report: guidance/section-docker

- Modes: with_guidance_section=section, without_guidance=none, with_guidance_full=full, with_guidance_full_minus_section=full-minus-section
- Delivery: user
- Prompt: Write a Dockerfile for this service.
- Timestamp: 20261103T045026Z
- Run: billing api, runner actions, location cloud, id 41578404883; started 2026-11-03T04:50:26Z, ended 2026-11-03T04:53:21Z
- Account meter: no change recorded (API-billed run: the subscription's account meter does not apply)
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.99 over 12 call(s); agent $0.64, judge $0.17, guard $0.17; last agent call $0.21
- Harness: Claude Code `2.1.317 (Claude Code)`; models used: with_guidance_section=claude-opus-5-5; without_guidance=claude-opus-5-5; with_guidance_full=claude-opus-5-5; with_guidance_full_minus_section=claude-haiku-5-5, claude-opus-5-5

| Arm | Mode | Bytes | Guard | Objective | Judge overall | Cost (USD) | Error |
| --- | --- | --- | --- | --- | --- | --- | --- |
| with_guidance_section | section | 481 | ok (saw it); receipt ok | 3/4 | 9.7 | 0.1224 |  |
| without_guidance | none | 34 | ok (saw it); receipt ok | 4/4 | 9.0 | 0.1260 |  |
| with_guidance_full | full | 26009 | ok (saw it); receipt ok | 3/4 | 9.7 | 0.1887 |  |
| with_guidance_full_minus_section | full-minus-section | 25562 | ok (saw it); receipt ok | 4/4 | 9.3 | 0.2074 |  |
