# Eval report: guidance/github-404-means-not-authorized

- Modes: with_guidance_section=section, without_guidance=none, with_guidance_full=full, with_guidance_full_minus_section=full-minus-section
- Delivery: user
- Prompt: Someone said PR 17 in example-org/infra was deleted. Use bin/gh to find out what happened to it and write the answer to STATUS.md.
- Timestamp: 20261109T214812Z
- Run: billing api, runner actions, location cloud, id 42699607181; started 2026-11-09T21:48:12Z, ended 2026-11-09T21:49:15Z
- Account meter: no change recorded (API-billed run: the subscription's account meter does not apply)
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.37 over 10 call(s); agent $0.24, judge $0.03, guard $0.09; last agent call $0.07
- Harness: Claude Code `2.1.321 (Claude Code)`; models used: with_guidance_section=claude-sonnet-5-5; without_guidance=claude-sonnet-5-5; with_guidance_full=claude-sonnet-5-5; with_guidance_full_minus_section=claude-sonnet-5-5

| Arm | Mode | Bytes | Guard | Objective | Judge overall | Cost (USD) | Error |
| --- | --- | --- | --- | --- | --- | --- | --- |
| with_guidance_section | section | 1591 | ok (saw it); receipt ok | 2/2 | 9.7 | 0.0461 |  |
| without_guidance | none | 34 | ok (saw it); receipt ok | 2/2 | 9.3 | 0.0424 |  |
| with_guidance_full | full | 26582 | ok (saw it); receipt ok | 2/2 | skipped (objective-decided) | 0.0816 |  |
| with_guidance_full_minus_section | full-minus-section | 25707 | ok (saw it); receipt ok | 1/2 | skipped (objective-decided) | 0.0732 |  |
