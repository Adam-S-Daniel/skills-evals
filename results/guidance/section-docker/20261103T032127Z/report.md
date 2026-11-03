# Eval report: guidance/section-docker

- Modes: with_guidance_section=section, without_guidance=none, with_guidance_full=full, with_guidance_full_minus_section=full-minus-section
- Delivery: user
- Prompt: Write a Dockerfile for this service.
- Timestamp: 20261103T032127Z
- Run: billing api, runner actions, location cloud, id 41570821022; started 2026-11-03T03:21:27Z, ended 2026-11-03T03:23:02Z
- Account meter: no change recorded (API-billed run: the subscription's account meter does not apply)
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.51 over 12 call(s); agent $0.27, judge $0.16, guard $0.09; last agent call $0.09
- Harness: Claude Code `2.1.317 (Claude Code)`; models used: with_guidance_section=claude-sonnet-5-5; without_guidance=claude-sonnet-5-5; with_guidance_full=claude-sonnet-5-5; with_guidance_full_minus_section=claude-sonnet-5-5

| Arm | Mode | Bytes | Guard | Objective | Judge overall | Cost (USD) | Error |
| --- | --- | --- | --- | --- | --- | --- | --- |
| with_guidance_section | section | 481 | ok (saw it); receipt ok | 4/4 | 9.7 | 0.0505 |  |
| without_guidance | none | 34 | ok (saw it); receipt ok | 4/4 | 9.0 | 0.0457 |  |
| with_guidance_full | full | 26009 | ok (saw it); receipt ok | 4/4 | 9.3 | 0.0857 |  |
| with_guidance_full_minus_section | full-minus-section | 25562 | ok (saw it); receipt ok | 4/4 | 9.0 | 0.0872 |  |
