# Eval report: guidance/section-dotnet

- Modes: with_guidance_section=section, without_guidance=none, with_guidance_full=full, with_guidance_full_minus_section=full-minus-section
- Delivery: user
- Prompt: Add LoadAsync() to SettingsStore: it reads the JSON file at the store's path into AppSettings, returning the defaults when the file does not exist. Also add a synchronous Load() for callers that cannot await.
- Timestamp: 20261103T032409Z
- Run: billing api, runner actions, location cloud, id 41570821022; started 2026-11-03T03:24:09Z, ended 2026-11-03T03:26:38Z
- Account meter: no change recorded (API-billed run: the subscription's account meter does not apply)
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.46 over 8 call(s); agent $0.37, judge $0.00, guard $0.09; last agent call $0.14
- Harness: Claude Code `2.1.317 (Claude Code)`; models used: with_guidance_section=claude-sonnet-5-5; without_guidance=claude-sonnet-5-5; with_guidance_full=claude-sonnet-5-5; with_guidance_full_minus_section=claude-sonnet-5-5

| Arm | Mode | Bytes | Guard | Objective | Judge overall | Cost (USD) | Error |
| --- | --- | --- | --- | --- | --- | --- | --- |
| with_guidance_section | section | 312 | ok (saw it); receipt ok | 3/3 | skipped (objective-decided) | 0.0583 |  |
| without_guidance | none | 34 | ok (saw it); receipt ok | 2/3 | skipped (objective-decided) | 0.0432 |  |
| with_guidance_full | full | 25840 | ok (saw it); receipt ok | 3/3 | skipped (objective-decided) | 0.1261 |  |
| with_guidance_full_minus_section | full-minus-section | 25562 | ok (saw it); receipt ok | 2/3 | skipped (objective-decided) | 0.1421 |  |
