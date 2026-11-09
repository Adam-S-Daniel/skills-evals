# Eval report: guidance/anything-you-name-gets-its-link

- Modes: with_guidance_section=section, without_guidance=none, with_guidance_full=full, with_guidance_full_minus_section=full-minus-section
- Delivery: user
- Prompt: Write HANDOFF.md for whoever picks this up tomorrow: what is done, what is blocked and on what, and what comes next. STATUS.json has the state of things.
- Timestamp: 20261109T195624Z
- Run: billing api, runner actions, location cloud, id 42682135656; started 2026-11-09T19:56:24Z, ended 2026-11-09T19:57:39Z
- Account meter: no change recorded (API-billed run: the subscription's account meter does not apply)
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.68 over 8 call(s); agent $0.50, judge $0.00, guard $0.18; last agent call $0.16
- Harness: Claude Code `2.1.321 (Claude Code)`; models used: with_guidance_section=claude-opus-5-5; without_guidance=claude-opus-5-5; with_guidance_full=claude-opus-5-5; with_guidance_full_minus_section=claude-opus-5-5

| Arm | Mode | Bytes | Guard | Objective | Judge overall | Cost (USD) | Error |
| --- | --- | --- | --- | --- | --- | --- | --- |
| with_guidance_section | section | 1602 | ok (saw it); receipt ok | 4/4 | skipped (objective-decided) | 0.0994 |  |
| without_guidance | none | 34 | ok (saw it); receipt ok | 0/4 | skipped (objective-decided) | 0.0931 |  |
| with_guidance_full | full | 26582 | ok (saw it); receipt ok | 4/4 | skipped (objective-decided) | 0.1497 |  |
| with_guidance_full_minus_section | full-minus-section | 25696 | ok (saw it); receipt ok | 0/4 | skipped (objective-decided) | 0.1605 |  |
