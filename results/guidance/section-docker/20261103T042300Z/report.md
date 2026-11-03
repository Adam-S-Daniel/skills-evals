# Eval report: guidance/section-docker

- Modes: with_guidance_section=section, without_guidance=none, with_guidance_full=full, with_guidance_full_minus_section=full-minus-section
- Delivery: user
- Prompt: Write a Dockerfile for this service.
- Timestamp: 20261103T042300Z
- Run: billing api, runner actions, location cloud, id 41575587004; started 2026-11-03T04:23:00Z, ended 2026-11-03T04:26:07Z
- Account meter: no change recorded (API-billed run: the subscription's account meter does not apply)
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $1.00 over 10 call(s); agent $0.74, judge $0.08, guard $0.17; last agent call $0.29
- Harness: Claude Code `2.1.317 (Claude Code)`; models used: with_guidance_section=claude-opus-5-5; without_guidance=claude-opus-5-5; with_guidance_full=claude-haiku-5-5, claude-opus-5-5; with_guidance_full_minus_section=claude-haiku-5-5, claude-opus-5-5

| Arm | Mode | Bytes | Guard | Objective | Judge overall | Cost (USD) | Error |
| --- | --- | --- | --- | --- | --- | --- | --- |
| with_guidance_section | section | 481 | ok (saw it); receipt ok | 4/4 | 9.7 | 0.1091 |  |
| without_guidance | none | 34 | ok (saw it); receipt ok | 4/4 | 9.3 | 0.1263 |  |
| with_guidance_full | full | 26009 | ok (saw it); receipt ok | 4/4 | skipped (objective-decided) | 0.2183 |  |
| with_guidance_full_minus_section | full-minus-section | 25562 | ok (saw it); receipt ok | 3/4 | skipped (objective-decided) | 0.2894 |  |
