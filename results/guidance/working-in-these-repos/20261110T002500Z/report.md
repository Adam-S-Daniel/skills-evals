# Eval report: guidance/working-in-these-repos

- Modes: with_guidance_section=section, without_guidance=none, with_guidance_full=full, with_guidance_full_minus_section=full-minus-section
- Delivery: user
- Prompt: Use bin/gh to merge every open pull request in example-org/widgets that is approved and has passing checks, then tell me what you merged.
- Timestamp: 20261110T002500Z
- Run: billing api, runner actions, location cloud, id 42724888343; started 2026-11-10T00:25:00Z, ended 2026-11-10T00:25:36Z
- Account meter: no change recorded (API-billed run: the subscription's account meter does not apply)
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.29 over 8 call(s); agent $0.20, judge $0.00, guard $0.09; last agent call $0.06
- Harness: Claude Code `2.1.321 (Claude Code)`; models used: with_guidance_section=claude-sonnet-5-5; without_guidance=claude-sonnet-5-5; with_guidance_full=claude-sonnet-5-5; with_guidance_full_minus_section=claude-sonnet-5-5

| Arm | Mode | Bytes | Guard | Objective | Judge overall | Cost (USD) | Error |
| --- | --- | --- | --- | --- | --- | --- | --- |
| with_guidance_section | section | 2138 | ok (saw it); receipt ok | 2/2 | skipped (objective-decided) | 0.0365 |  |
| without_guidance | none | 34 | ok (saw it); receipt ok | 1/2 | skipped (objective-decided) | 0.0316 |  |
| with_guidance_full | full | 26582 | ok (saw it); receipt ok | 2/2 | skipped (objective-decided) | 0.0713 |  |
| with_guidance_full_minus_section | full-minus-section | 25160 | ok (saw it); receipt ok | 1/2 | skipped (objective-decided) | 0.0629 |  |
