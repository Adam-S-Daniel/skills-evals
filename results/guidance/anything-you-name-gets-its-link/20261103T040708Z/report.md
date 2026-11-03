# Eval report: guidance/anything-you-name-gets-its-link

- Modes: with_guidance_section=section, without_guidance=none, with_guidance_full=full, with_guidance_full_minus_section=full-minus-section
- Delivery: user
- Prompt: Write NEXT.md: what I am waiting on before I can open the v2.4.0 release pull request. STATUS.json has the state of things.
- Timestamp: 20261103T040708Z
- Run: billing api, runner actions, location cloud, id 41575587004; started 2026-11-03T04:07:08Z, ended 2026-11-03T04:08:07Z
- Account meter: no change recorded (API-billed run: the subscription's account meter does not apply)
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.64 over 8 call(s); agent $0.47, judge $0.00, guard $0.17; last agent call $0.16
- Harness: Claude Code `2.1.317 (Claude Code)`; models used: with_guidance_section=claude-opus-5-5; without_guidance=claude-opus-5-5; with_guidance_full=claude-opus-5-5; with_guidance_full_minus_section=claude-opus-5-5

| Arm | Mode | Bytes | Guard | Objective | Judge overall | Cost (USD) | Error |
| --- | --- | --- | --- | --- | --- | --- | --- |
| with_guidance_section | section | 1602 | ok (saw it); receipt ok | 3/3 | skipped (objective-decided) | 0.0810 |  |
| without_guidance | none | 34 | ok (saw it); receipt ok | 1/3 | skipped (objective-decided) | 0.0822 |  |
| with_guidance_full | full | 25562 | ok (saw it); receipt ok | 3/3 | skipped (objective-decided) | 0.1504 |  |
| with_guidance_full_minus_section | full-minus-section | 24676 | ok (saw it); receipt ok | 1/3 | skipped (objective-decided) | 0.1571 |  |
