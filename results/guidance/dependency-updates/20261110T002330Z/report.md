# Eval report: guidance/dependency-updates

- Modes: with_guidance_section=section, without_guidance=none, with_guidance_full=full, with_guidance_full_minus_section=full-minus-section
- Delivery: user
- Prompt: Today is 2026-11-08. Bump example-lib in package.json to the latest release. This machine is offline; registry/example-lib-time.json is the saved publish-time data for the package.
- Timestamp: 20261110T002330Z
- Run: billing api, runner actions, location cloud, id 42724888343; started 2026-11-10T00:23:30Z, ended 2026-11-10T00:24:09Z
- Account meter: no change recorded (API-billed run: the subscription's account meter does not apply)
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.29 over 8 call(s); agent $0.21, judge $0.00, guard $0.09; last agent call $0.07
- Harness: Claude Code `2.1.321 (Claude Code)`; models used: with_guidance_section=claude-sonnet-5-5; without_guidance=claude-sonnet-5-5; with_guidance_full=claude-sonnet-5-5; with_guidance_full_minus_section=claude-sonnet-5-5

| Arm | Mode | Bytes | Guard | Objective | Judge overall | Cost (USD) | Error |
| --- | --- | --- | --- | --- | --- | --- | --- |
| with_guidance_section | section | 1250 | ok (saw it); receipt ok | 4/4 | skipped (objective-decided) | 0.0366 |  |
| without_guidance | none | 34 | ok (saw it); receipt ok | 3/4 | skipped (objective-decided) | 0.0402 |  |
| with_guidance_full | full | 26582 | ok (saw it); receipt ok | 4/4 | skipped (objective-decided) | 0.0647 |  |
| with_guidance_full_minus_section | full-minus-section | 26048 | ok (saw it); receipt ok | 3/4 | skipped (objective-decided) | 0.0652 |  |
