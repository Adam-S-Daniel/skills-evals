# Eval report: guidance/anything-you-name-gets-its-link

- Modes: with_guidance_section=section, without_guidance=none, with_guidance_full=full, with_guidance_full_minus_section=full-minus-section
- Delivery: user
- Prompt: PR 58 in example-org/ledger still can't merge. The exports in snapshot/ are current. Tell me in a sentence or two what I have to do to unblock it.
- Timestamp: 20261109T201318Z
- Run: billing api, runner actions, location cloud, id 42686615747; started 2026-11-09T20:13:18Z, ended 2026-11-09T20:13:54Z
- Account meter: no change recorded (API-billed run: the subscription's account meter does not apply)
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.30 over 8 call(s); agent $0.21, judge $0.00, guard $0.09; last agent call $0.07
- Harness: Claude Code `2.1.321 (Claude Code)`; models used: with_guidance_section=claude-sonnet-5-5; without_guidance=claude-sonnet-5-5; with_guidance_full=claude-sonnet-5-5; with_guidance_full_minus_section=claude-sonnet-5-5

| Arm | Mode | Bytes | Guard | Objective | Judge overall | Cost (USD) | Error |
| --- | --- | --- | --- | --- | --- | --- | --- |
| with_guidance_section | section | 1602 | ok (saw it); receipt ok | 1/2 | skipped (objective-decided) | 0.0387 |  |
| without_guidance | none | 34 | ok (saw it); receipt ok | 0/2 | skipped (objective-decided) | 0.0367 |  |
| with_guidance_full | full | 26582 | ok (saw it); receipt ok | 1/2 | skipped (objective-decided) | 0.0688 |  |
| with_guidance_full_minus_section | full-minus-section | 25696 | ok (saw it); receipt ok | 0/2 | skipped (objective-decided) | 0.0698 |  |
