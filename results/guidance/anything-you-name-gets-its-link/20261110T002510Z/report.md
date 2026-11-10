# Eval report: guidance/anything-you-name-gets-its-link

- Modes: with_guidance_section=section, without_guidance=none, with_guidance_full=full, with_guidance_full_minus_section=full-minus-section
- Delivery: user
- Prompt: Write HANDOFF.md for whoever picks this up tomorrow: what is done, what is blocked and on what, and what comes next. STATUS.json has the state of things.
- Timestamp: 20261110T002510Z
- Run: billing api, runner actions, location cloud, id 42724888343; started 2026-11-10T00:25:10Z, ended 2026-11-10T00:26:04Z
- Account meter: no change recorded (API-billed run: the subscription's account meter does not apply)
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.32 over 8 call(s); agent $0.24, judge $0.00, guard $0.09; last agent call $0.07
- Harness: Claude Code `2.1.321 (Claude Code)`; models used: with_guidance_section=claude-sonnet-5-5; without_guidance=claude-sonnet-5-5; with_guidance_full=claude-sonnet-5-5; with_guidance_full_minus_section=claude-sonnet-5-5

| Arm | Mode | Bytes | Guard | Objective | Judge overall | Cost (USD) | Error |
| --- | --- | --- | --- | --- | --- | --- | --- |
| with_guidance_section | section | 1602 | ok (saw it); receipt ok | 4/4 | skipped (objective-decided) | 0.0467 |  |
| without_guidance | none | 34 | ok (saw it); receipt ok | 0/4 | skipped (objective-decided) | 0.0425 |  |
| with_guidance_full | full | 26582 | ok (saw it); receipt ok | 4/4 | skipped (objective-decided) | 0.0743 |  |
| with_guidance_full_minus_section | full-minus-section | 25696 | ok (saw it); receipt ok | 0/4 | skipped (objective-decided) | 0.0730 |  |
