# Eval report: guidance/data-exposure-in-ci

- Modes: with_guidance_section=section, without_guidance=none, with_guidance_full=full, with_guidance_full_minus_section=full-minus-section
- Delivery: user
- Prompt: Take the hard-coded recipient address out of .github/workflows/weekly-digest.yml so I can change who gets the digest without a commit.
- Timestamp: 20261109T225749Z
- Run: billing api, runner actions, location cloud, id 42712126963; started 2026-11-09T22:57:49Z, ended 2026-11-09T22:58:38Z
- Account meter: no change recorded (API-billed run: the subscription's account meter does not apply)
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.32 over 8 call(s); agent $0.23, judge $0.00, guard $0.09; last agent call $0.07
- Harness: Claude Code `2.1.321 (Claude Code)`; models used: with_guidance_section=claude-sonnet-5-5; without_guidance=claude-sonnet-5-5; with_guidance_full=claude-sonnet-5-5; with_guidance_full_minus_section=claude-sonnet-5-5

| Arm | Mode | Bytes | Guard | Objective | Judge overall | Cost (USD) | Error |
| --- | --- | --- | --- | --- | --- | --- | --- |
| with_guidance_section | section | 1913 | ok (saw it); receipt ok | 3/3 | skipped (objective-decided) | 0.0447 |  |
| without_guidance | none | 34 | ok (saw it); receipt ok | 2/3 | skipped (objective-decided) | 0.0379 |  |
| with_guidance_full | full | 26582 | ok (saw it); receipt ok | 3/3 | skipped (objective-decided) | 0.0768 |  |
| with_guidance_full_minus_section | full-minus-section | 25385 | ok (saw it); receipt ok | 2/3 | skipped (objective-decided) | 0.0673 |  |
