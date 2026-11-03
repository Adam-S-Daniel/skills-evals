# Eval report: guidance/section-python

- Modes: with_guidance_section=section, without_guidance=none, with_guidance_full=full, with_guidance_full_minus_section=full-minus-section
- Delivery: user
- Prompt: Add load_settings(path) to settings.py: it reads a JSON file of overrides and returns merged(overrides). If the file is missing or is not valid JSON, report it and return the defaults.
- Timestamp: 20261103T035332Z
- Run: billing api, runner actions, location cloud, id 41573472429; started 2026-11-03T03:53:32Z, ended 2026-11-03T03:55:43Z
- Account meter: no change recorded (API-billed run: the subscription's account meter does not apply)
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.86 over 8 call(s); agent $0.69, judge $0.00, guard $0.17; last agent call $0.20
- Harness: Claude Code `2.1.317 (Claude Code)`; models used: with_guidance_section=claude-opus-5-5; without_guidance=claude-opus-5-5; with_guidance_full=claude-opus-5-5, claude-sonnet-5-5; with_guidance_full_minus_section=claude-haiku-5-5, claude-opus-5-5

| Arm | Mode | Bytes | Guard | Objective | Judge overall | Cost (USD) | Error |
| --- | --- | --- | --- | --- | --- | --- | --- |
| with_guidance_section | section | 820 | ok (saw it); receipt ok | 4/4 | skipped (objective-decided) | 0.1111 |  |
| without_guidance | none | 34 | ok (saw it); receipt ok | 3/4 | skipped (objective-decided) | 0.0987 |  |
| with_guidance_full | full | 26348 | ok (saw it); receipt ok | 4/4 | skipped (objective-decided) | 0.2811 |  |
| with_guidance_full_minus_section | full-minus-section | 25562 | ok (saw it); receipt ok | 3/4 | skipped (objective-decided) | 0.1979 |  |
