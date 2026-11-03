# Eval report: guidance/section-dotnet

- Modes: with_guidance_section=section, without_guidance=none, with_guidance_full=full, with_guidance_full_minus_section=full-minus-section
- Delivery: user
- Prompt: Add LoadAsync() to SettingsStore: it reads the JSON file at the store's path into AppSettings, returning the defaults when the file does not exist. Also add a synchronous Load() for callers that cannot await.
- Timestamp: 20261103T050726Z
- Run: billing api, runner actions, location cloud, id 41581432158; started 2026-11-03T05:07:26Z, ended 2026-11-03T05:11:51Z
- Account meter: no change recorded (API-billed run: the subscription's account meter does not apply)
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $1.13 over 8 call(s); agent $0.96, judge $0.00, guard $0.17; last agent call $0.37
- Harness: Claude Code `2.1.317 (Claude Code)`; models used: with_guidance_section=claude-opus-5-5; without_guidance=claude-opus-5-5; with_guidance_full=claude-haiku-5-5, claude-opus-5-5; with_guidance_full_minus_section=claude-opus-5-5, claude-sonnet-5-5

| Arm | Mode | Bytes | Guard | Objective | Judge overall | Cost (USD) | Error |
| --- | --- | --- | --- | --- | --- | --- | --- |
| with_guidance_section | section | 312 | ok (saw it); receipt ok | 3/3 | skipped (objective-decided) | 0.1368 |  |
| without_guidance | none | 34 | ok (saw it); receipt ok | 2/3 | skipped (objective-decided) | 0.1228 |  |
| with_guidance_full | full | 25840 | ok (saw it); receipt ok | 3/3 | skipped (objective-decided) | 0.3303 |  |
| with_guidance_full_minus_section | full-minus-section | 25562 | ok (saw it); receipt ok | 2/3 | skipped (objective-decided) | 0.3676 |  |
