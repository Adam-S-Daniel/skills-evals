# Eval report: guidance/section-typescript

- Modes: with_guidance_section=section, without_guidance=none, with_guidance_full=full, with_guidance_full_minus_section=full-minus-section
- Delivery: user
- Prompt: Add parseEvent(raw: string): Event to src/events.ts. It parses a JSON webhook payload and throws if the payload is not a valid Event.
- Timestamp: 20261103T030138Z
- Run: billing api, runner actions, location cloud, id 41568178365; started 2026-11-03T03:01:38Z, ended 2026-11-03T03:02:40Z
- Account meter: no change recorded (API-billed run: the subscription's account meter does not apply)
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.40 over 10 call(s); agent $0.22, judge $0.08, guard $0.11; last agent call $0.07
- Harness: Claude Code `2.1.317 (Claude Code)`; models used: with_guidance_section=claude-sonnet-5-5; without_guidance=claude-sonnet-5-5; with_guidance_full=claude-sonnet-5-5; with_guidance_full_minus_section=claude-sonnet-5-5

| Arm | Mode | Bytes | Guard | Objective | Judge overall | Cost (USD) | Error |
| --- | --- | --- | --- | --- | --- | --- | --- |
| with_guidance_section | section | 560 | ok (saw it); receipt ok | 3/3 | 9.7 | 0.0393 |  |
| without_guidance | none | 34 | ok (saw it); receipt ok | 3/3 | 9.3 | 0.0358 |  |
| with_guidance_full | full | 26088 | ok (saw it); receipt ok | 3/3 | skipped (objective-decided) | 0.0677 |  |
| with_guidance_full_minus_section | full-minus-section | 25562 | ok (saw it); receipt ok | 2/3 | skipped (objective-decided) | 0.0726 |  |
