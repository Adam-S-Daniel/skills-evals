# Eval report: guidance/working-in-these-repos

- Modes: with_guidance_section=section, without_guidance=none, with_guidance_full=full, with_guidance_full_minus_section=full-minus-section
- Delivery: user
- Prompt: Use bin/gh to merge every open pull request in example-org/widgets that is approved and has passing checks, then tell me what you merged.
- Timestamp: 20261103T061439Z
- Run: billing api, runner actions, location cloud, id 41587675812; started 2026-11-03T06:14:39Z, ended 2026-11-03T06:16:06Z
- Account meter: no change recorded (API-billed run: the subscription's account meter does not apply)
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.80 over 12 call(s); agent $0.49, judge $0.14, guard $0.17; last agent call $0.16
- Harness: Claude Code `2.1.317 (Claude Code)`; models used: with_guidance_section=claude-opus-5-5; without_guidance=claude-opus-5-5; with_guidance_full=claude-opus-5-5; with_guidance_full_minus_section=claude-opus-5-5

| Arm | Mode | Bytes | Guard | Objective | Judge overall | Cost (USD) | Error |
| --- | --- | --- | --- | --- | --- | --- | --- |
| with_guidance_section | section | 2138 | ok (saw it); receipt ok | 2/2 | 9.7 | 0.0881 |  |
| without_guidance | none | 34 | ok (saw it); receipt ok | 2/2 | 9.0 | 0.0909 |  |
| with_guidance_full | full | 25562 | ok (saw it); receipt ok | 2/2 | 10.0 | 0.1484 |  |
| with_guidance_full_minus_section | full-minus-section | 24140 | ok (saw it); receipt ok | 2/2 | 9.7 | 0.1629 |  |
