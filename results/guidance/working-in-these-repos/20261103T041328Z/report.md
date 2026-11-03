# Eval report: guidance/working-in-these-repos

- Modes: with_guidance_section=section, without_guidance=none, with_guidance_full=full, with_guidance_full_minus_section=full-minus-section
- Delivery: user
- Prompt: Use bin/gh to merge every open pull request in example-org/widgets that is approved and has passing checks, then tell me what you merged.
- Timestamp: 20261103T041328Z
- Run: billing api, runner actions, location cloud, id 41575587004; started 2026-11-03T04:13:28Z, ended 2026-11-03T04:14:54Z
- Account meter: no change recorded (API-billed run: the subscription's account meter does not apply)
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.78 over 12 call(s); agent $0.47, judge $0.13, guard $0.17; last agent call $0.15
- Harness: Claude Code `2.1.317 (Claude Code)`; models used: with_guidance_section=claude-opus-5-5; without_guidance=claude-opus-5-5; with_guidance_full=claude-opus-5-5; with_guidance_full_minus_section=claude-opus-5-5

| Arm | Mode | Bytes | Guard | Objective | Judge overall | Cost (USD) | Error |
| --- | --- | --- | --- | --- | --- | --- | --- |
| with_guidance_section | section | 2138 | ok (saw it); receipt ok | 2/2 | 10.0 | 0.0790 |  |
| without_guidance | none | 34 | ok (saw it); receipt ok | 2/2 | 8.7 | 0.0864 |  |
| with_guidance_full | full | 25562 | ok (saw it); receipt ok | 2/2 | 10.0 | 0.1541 |  |
| with_guidance_full_minus_section | full-minus-section | 24140 | ok (saw it); receipt ok | 2/2 | 9.7 | 0.1525 |  |
