# Eval report: guidance/dependency-updates

- Modes: with_guidance_section=section, without_guidance=none, with_guidance_full=full, with_guidance_full_minus_section=full-minus-section
- Delivery: user
- Prompt: Today is 2026-11-08. Bump example-lib in package.json to the latest release. This machine is offline; registry/example-lib-time.json is the saved publish-time data for the package.
- Timestamp: 20261110T000726Z
- Run: billing api, runner actions, location cloud, id 42722279274; started 2026-11-10T00:07:26Z, ended 2026-11-10T00:08:45Z
- Account meter: no change recorded (API-billed run: the subscription's account meter does not apply)
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.67 over 10 call(s); agent $0.46, judge $0.03, guard $0.18; last agent call $0.17
- Harness: Claude Code `2.1.321 (Claude Code)`; models used: with_guidance_section=claude-opus-5-5; without_guidance=claude-opus-5-5; with_guidance_full=claude-opus-5-5; with_guidance_full_minus_section=claude-opus-5-5

| Arm | Mode | Bytes | Guard | Objective | Judge overall | Cost (USD) | Error |
| --- | --- | --- | --- | --- | --- | --- | --- |
| with_guidance_section | section | 1250 | ok (saw it); receipt ok | 4/4 | skipped (objective-decided) | 0.0761 |  |
| without_guidance | none | 34 | ok (saw it); receipt ok | 3/4 | skipped (objective-decided) | 0.0799 |  |
| with_guidance_full | full | 26582 | ok (saw it); receipt ok | 4/4 | 10.0 | 0.1374 |  |
| with_guidance_full_minus_section | full-minus-section | 26048 | ok (saw it); receipt ok | 4/4 | 9.7 | 0.1688 |  |
