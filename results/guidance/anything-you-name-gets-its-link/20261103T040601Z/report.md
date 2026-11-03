# Eval report: guidance/anything-you-name-gets-its-link

- Modes: with_guidance_section=section, without_guidance=none, with_guidance_full=full, with_guidance_full_minus_section=full-minus-section
- Delivery: user
- Prompt: Write HANDOFF.md for whoever picks this up tomorrow: what is done, what is blocked and on what, and what comes next. STATUS.json has the state of things.
- Timestamp: 20261103T040601Z
- Run: billing api, runner actions, location cloud, id 41575587004; started 2026-11-03T04:06:01Z, ended 2026-11-03T04:07:20Z
- Account meter: no change recorded (API-billed run: the subscription's account meter does not apply)
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.67 over 8 call(s); agent $0.49, judge $0.00, guard $0.17; last agent call $0.15
- Harness: Claude Code `2.1.317 (Claude Code)`; models used: with_guidance_section=claude-opus-5-5; without_guidance=claude-opus-5-5; with_guidance_full=claude-opus-5-5; with_guidance_full_minus_section=claude-opus-5-5

| Arm | Mode | Bytes | Guard | Objective | Judge overall | Cost (USD) | Error |
| --- | --- | --- | --- | --- | --- | --- | --- |
| with_guidance_section | section | 1602 | ok (saw it); receipt ok | 4/4 | skipped (objective-decided) | 0.0962 |  |
| without_guidance | none | 34 | ok (saw it); receipt ok | 0/4 | skipped (objective-decided) | 0.0904 |  |
| with_guidance_full | full | 25562 | ok (saw it); receipt ok | 4/4 | skipped (objective-decided) | 0.1583 |  |
| with_guidance_full_minus_section | full-minus-section | 24676 | ok (saw it); receipt ok | 0/4 | skipped (objective-decided) | 0.1482 |  |
