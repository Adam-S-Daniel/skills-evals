# Eval report: guidance/working-in-these-repos

- Modes: with_guidance_section=section, without_guidance=none, with_guidance_full=full, with_guidance_full_minus_section=full-minus-section
- Delivery: user
- Prompt: Use bin/gh to merge every open pull request in example-org/widgets that is approved and has passing checks, then tell me what you merged.
- Timestamp: 20261103T034759Z
- Run: billing api, runner actions, location cloud, id 41573472429; started 2026-11-03T03:47:59Z, ended 2026-11-03T03:49:25Z
- Account meter: no change recorded (API-billed run: the subscription's account meter does not apply)
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.80 over 12 call(s); agent $0.50, judge $0.13, guard $0.17; last agent call $0.17
- Harness: Claude Code `2.1.317 (Claude Code)`; models used: with_guidance_section=claude-opus-5-5; without_guidance=claude-opus-5-5; with_guidance_full=claude-opus-5-5; with_guidance_full_minus_section=claude-opus-5-5

| Arm | Mode | Bytes | Guard | Objective | Judge overall | Cost (USD) | Error |
| --- | --- | --- | --- | --- | --- | --- | --- |
| with_guidance_section | section | 2138 | ok (saw it); receipt ok | 2/2 | 10.0 | 0.0842 |  |
| without_guidance | none | 34 | ok (saw it); receipt ok | 2/2 | 9.0 | 0.0909 |  |
| with_guidance_full | full | 25562 | ok (saw it); receipt ok | 2/2 | 10.0 | 0.1527 |  |
| with_guidance_full_minus_section | full-minus-section | 24140 | ok (saw it); receipt ok | 2/2 | 9.3 | 0.1703 |  |
