# Eval report: guidance/section-python

- Modes: with_guidance_section=section, without_guidance=none, with_guidance_full=full, with_guidance_full_minus_section=full-minus-section
- Delivery: user
- Prompt: Add load_settings(path) to settings.py: it reads a JSON file of overrides and returns merged(overrides). If the file is missing or is not valid JSON, report it and return the defaults.
- Timestamp: 20261103T023230Z
- Run: billing api, runner actions, location cloud, id 41565470204; started 2026-11-03T02:32:30Z, ended 2026-11-03T02:34:02Z
- Account meter: no change recorded (API-billed run: the subscription's account meter does not apply)
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.38 over 8 call(s); agent $0.29, judge $0.00, guard $0.09; last agent call $0.10
- Harness: Claude Code `2.1.317 (Claude Code)`; models used: with_guidance_section=claude-sonnet-5-5; without_guidance=claude-sonnet-5-5; with_guidance_full=claude-sonnet-5-5; with_guidance_full_minus_section=claude-sonnet-5-5

| Arm | Mode | Bytes | Guard | Objective | Judge overall | Cost (USD) | Error |
| --- | --- | --- | --- | --- | --- | --- | --- |
| with_guidance_section | section | 820 | ok (saw it); receipt ok | 4/4 | skipped (objective-decided) | 0.0471 |  |
| without_guidance | none | 34 | ok (saw it); receipt ok | 2/4 | skipped (objective-decided) | 0.0394 |  |
| with_guidance_full | full | 26348 | ok (saw it); receipt ok | 4/4 | skipped (objective-decided) | 0.1008 |  |
| with_guidance_full_minus_section | full-minus-section | 25562 | ok (saw it); receipt ok | 3/4 | skipped (objective-decided) | 0.1043 |  |
