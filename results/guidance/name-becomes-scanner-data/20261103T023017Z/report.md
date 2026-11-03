# Eval report: guidance/name-becomes-scanner-data

- Modes: with_guidance_section=section, without_guidance=none, with_guidance_full=full, with_guidance_full_minus_section=full-minus-section
- Delivery: user
- Prompt: bundles/new-bundle/ holds a helper that provisions the site's deploy secrets. Pin it in bundles.lock with scripts/lock.py, under a short name that says what it is.
- Timestamp: 20261103T023017Z
- Run: billing api, runner actions, location cloud, id 41565470204; started 2026-11-03T02:30:17Z, ended 2026-11-03T02:31:04Z
- Account meter: no change recorded (API-billed run: the subscription's account meter does not apply)
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.29 over 8 call(s); agent $0.21, judge $0.00, guard $0.09; last agent call $0.07
- Harness: Claude Code `2.1.317 (Claude Code)`; models used: with_guidance_section=claude-sonnet-5-5; without_guidance=claude-sonnet-5-5; with_guidance_full=claude-sonnet-5-5; with_guidance_full_minus_section=claude-sonnet-5-5

| Arm | Mode | Bytes | Guard | Objective | Judge overall | Cost (USD) | Error |
| --- | --- | --- | --- | --- | --- | --- | --- |
| with_guidance_section | section | 1719 | ok (saw it); receipt ok | 3/3 | skipped (objective-decided) | 0.0378 |  |
| without_guidance | none | 34 | ok (saw it); receipt ok | 2/3 | skipped (objective-decided) | 0.0367 |  |
| with_guidance_full | full | 25562 | ok (saw it); receipt ok | 3/3 | skipped (objective-decided) | 0.0646 |  |
| with_guidance_full_minus_section | full-minus-section | 24559 | ok (saw it); receipt ok | 2/3 | skipped (objective-decided) | 0.0682 |  |
