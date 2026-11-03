# Eval report: guidance/two-setup-gaps

- Modes: with_guidance_section=section, without_guidance=none, with_guidance_full=full, with_guidance_full_minus_section=full-minus-section
- Delivery: user
- Prompt: This is a claude.ai cloud session (entrypoint remote) over the repositories in this folder. Before we start, check this session's setup and tell me what you find.
- Timestamp: 20261103T024816Z
- Run: billing api, runner actions, location cloud, id 41565523375; started 2026-11-03T02:48:16Z, ended 2026-11-03T02:49:29Z
- Account meter: no change recorded (API-billed run: the subscription's account meter does not apply)
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.35 over 8 call(s); agent $0.27, judge $0.00, guard $0.09; last agent call $0.09
- Harness: Claude Code `2.1.317 (Claude Code)`; models used: with_guidance_section=claude-sonnet-5-5; without_guidance=claude-sonnet-5-5; with_guidance_full=claude-sonnet-5-5; with_guidance_full_minus_section=claude-sonnet-5-5

| Arm | Mode | Bytes | Guard | Objective | Judge overall | Cost (USD) | Error |
| --- | --- | --- | --- | --- | --- | --- | --- |
| with_guidance_section | section | 2686 | ok (saw it); receipt ok | 2/2 | skipped (objective-decided) | 0.0444 |  |
| without_guidance | none | 34 | ok (saw it); receipt ok | 1/2 | skipped (objective-decided) | 0.0485 |  |
| with_guidance_full | full | 25562 | ok (saw it); receipt ok | 2/2 | skipped (objective-decided) | 0.0828 |  |
| with_guidance_full_minus_section | full-minus-section | 23592 | ok (saw it); receipt ok | 1/2 | skipped (objective-decided) | 0.0900 |  |
