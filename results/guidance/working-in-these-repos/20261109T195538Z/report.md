# Eval report: guidance/working-in-these-repos

- Modes: with_guidance_section=section, without_guidance=none, with_guidance_full=full, with_guidance_full_minus_section=full-minus-section
- Delivery: user
- Prompt: Use bin/gh to merge every open pull request in example-org/widgets that is approved and has passing checks, then tell me what you merged.
- Timestamp: 20261109T195538Z
- Run: billing api, runner actions, location cloud, id 42682135656; started 2026-11-09T19:55:38Z, ended 2026-11-09T19:56:56Z
- Account meter: no change recorded (API-billed run: the subscription's account meter does not apply)
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.71 over 12 call(s); agent $0.47, judge $0.06, guard $0.18; last agent call $0.15
- Harness: Claude Code `2.1.321 (Claude Code)`; models used: with_guidance_section=claude-opus-5-5; without_guidance=claude-opus-5-5; with_guidance_full=claude-opus-5-5; with_guidance_full_minus_section=claude-opus-5-5

| Arm | Mode | Bytes | Guard | Objective | Judge overall | Cost (USD) | Error |
| --- | --- | --- | --- | --- | --- | --- | --- |
| with_guidance_section | section | 2138 | ok (saw it); receipt ok | 2/2 | 10.0 | 0.0776 |  |
| without_guidance | none | 34 | ok (saw it); receipt ok | 2/2 | 8.7 | 0.0917 |  |
| with_guidance_full | full | 26582 | ok (saw it); receipt ok | 2/2 | 9.0 | 0.1494 |  |
| with_guidance_full_minus_section | full-minus-section | 25160 | ok (saw it); receipt ok | 2/2 | 9.3 | 0.1544 |  |
