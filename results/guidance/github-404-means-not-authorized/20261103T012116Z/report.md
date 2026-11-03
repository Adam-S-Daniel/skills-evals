# Eval report: guidance/github-404-means-not-authorized

- Modes: with_guidance_section=section, without_guidance=none, with_guidance_full=full, with_guidance_full_minus_section=full-minus-section
- Delivery: user
- Prompt: Someone said PR 17 in example-org/infra was deleted. Use bin/gh to find out what happened to it and write the answer to STATUS.md.
- Timestamp: 20261103T012116Z
- Run: billing api, runner actions, location cloud, id 41557705869; started 2026-11-03T01:21:16Z, ended 2026-11-03T01:22:21Z
- Account meter: no change recorded (API-billed run: the subscription's account meter does not apply)
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.33 over 8 call(s); agent $0.24, judge $0.00, guard $0.09; last agent call $0.07
- Harness: Claude Code `2.1.316 (Claude Code)`; models used: with_guidance_section=claude-sonnet-5-5; without_guidance=claude-sonnet-5-5; with_guidance_full=claude-sonnet-5-5; with_guidance_full_minus_section=claude-sonnet-5-5

| Arm | Mode | Bytes | Guard | Objective | Judge overall | Cost (USD) | Error |
| --- | --- | --- | --- | --- | --- | --- | --- |
| with_guidance_section | section | 1591 | ok (saw it); receipt ok | 2/2 | skipped (objective-decided) | 0.0437 |  |
| without_guidance | none | 34 | ok (saw it); receipt ok | 1/2 | skipped (objective-decided) | 0.0428 |  |
| with_guidance_full | full | 25562 | ok (saw it); receipt ok | 2/2 | skipped (objective-decided) | 0.0795 |  |
| with_guidance_full_minus_section | full-minus-section | 24687 | ok (saw it); receipt ok | 1/2 | skipped (objective-decided) | 0.0745 |  |
