# Eval report: guidance/anything-you-name-gets-its-link

- Modes: with_guidance_section=section, without_guidance=none, with_guidance_full=full, with_guidance_full_minus_section=full-minus-section
- Delivery: user
- Prompt: Write DONE.md, a short summary of what landed this week, from STATUS.json.
- Timestamp: 20261110T000925Z
- Run: billing api, runner actions, location cloud, id 42722279274; started 2026-11-10T00:09:25Z, ended 2026-11-10T00:10:22Z
- Account meter: no change recorded (API-billed run: the subscription's account meter does not apply)
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.63 over 8 call(s); agent $0.45, judge $0.00, guard $0.18; last agent call $0.14
- Harness: Claude Code `2.1.321 (Claude Code)`; models used: with_guidance_section=claude-opus-5-5; without_guidance=claude-opus-5-5; with_guidance_full=claude-opus-5-5; with_guidance_full_minus_section=claude-opus-5-5

| Arm | Mode | Bytes | Guard | Objective | Judge overall | Cost (USD) | Error |
| --- | --- | --- | --- | --- | --- | --- | --- |
| with_guidance_section | section | 1602 | ok (saw it); receipt ok | 3/3 | skipped (objective-decided) | 0.0853 |  |
| without_guidance | none | 34 | ok (saw it); receipt ok | 0/3 | skipped (objective-decided) | 0.0728 |  |
| with_guidance_full | full | 26582 | ok (saw it); receipt ok | 3/3 | skipped (objective-decided) | 0.1546 |  |
| with_guidance_full_minus_section | full-minus-section | 25696 | ok (saw it); receipt ok | 0/3 | skipped (objective-decided) | 0.1372 |  |
