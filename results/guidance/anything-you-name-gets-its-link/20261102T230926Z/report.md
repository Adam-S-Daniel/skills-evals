# Eval report: guidance/anything-you-name-gets-its-link

- Modes: with_guidance_section=section, without_guidance=none, with_guidance_full=full, with_guidance_full_minus_section=full-minus-section
- Delivery: user
- Prompt: Write DONE.md, a short summary of what landed this week, from STATUS.json.
- Timestamp: 20261102T230926Z
- Run: billing api, runner actions, location cloud, id 41542886876; started 2026-11-02T23:09:26Z, ended 2026-11-02T23:10:07Z
- Account meter: no change recorded (API-billed run: the subscription's account meter does not apply)
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.31 over 8 call(s); agent $0.21, judge $0.00, guard $0.11; last agent call $0.07
- Harness: Claude Code `2.1.316 (Claude Code)`; models used: with_guidance_section=claude-sonnet-5-5; without_guidance=claude-sonnet-5-5; with_guidance_full=claude-sonnet-5-5; with_guidance_full_minus_section=claude-sonnet-5-5

| Arm | Mode | Bytes | Guard | Objective | Judge overall | Cost (USD) | Error |
| --- | --- | --- | --- | --- | --- | --- | --- |
| with_guidance_section | section | 1602 | ok (saw it); receipt ok | 3/3 | skipped (objective-decided) | 0.0415 |  |
| without_guidance | none | 34 | ok (saw it); receipt ok | 0/3 | skipped (objective-decided) | 0.0332 |  |
| with_guidance_full | full | 25562 | ok (saw it); receipt ok | 3/3 | skipped (objective-decided) | 0.0653 |  |
| with_guidance_full_minus_section | full-minus-section | 24676 | ok (saw it); receipt ok | 0/3 | skipped (objective-decided) | 0.0650 |  |
