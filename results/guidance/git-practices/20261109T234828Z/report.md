# Eval report: guidance/git-practices

- Modes: with_guidance_section=section, without_guidance=none, with_guidance_full=full, with_guidance_full_minus_section=full-minus-section
- Delivery: user
- Prompt: PR 7 in example-org/widgets is approved and green; merge it with bin/gh. It is one step of issue #12, which still has work left, so mention #12 in the merge commit.
- Timestamp: 20261109T234828Z
- Run: billing api, runner actions, location cloud, id 42718601638; started 2026-11-09T23:48:28Z, ended 2026-11-09T23:49:15Z
- Account meter: no change recorded (API-billed run: the subscription's account meter does not apply)
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.33 over 10 call(s); agent $0.21, judge $0.04, guard $0.09; last agent call $0.07
- Harness: Claude Code `2.1.321 (Claude Code)`; models used: with_guidance_section=claude-sonnet-5-5; without_guidance=claude-sonnet-5-5; with_guidance_full=claude-sonnet-5-5; with_guidance_full_minus_section=claude-sonnet-5-5

| Arm | Mode | Bytes | Guard | Objective | Judge overall | Cost (USD) | Error |
| --- | --- | --- | --- | --- | --- | --- | --- |
| with_guidance_section | section | 2112 | ok (saw it); receipt ok | 2/2 | skipped (objective-decided) | 0.0324 |  |
| without_guidance | none | 34 | ok (saw it); receipt ok | 1/2 | skipped (objective-decided) | 0.0351 |  |
| with_guidance_full | full | 26582 | ok (saw it); receipt ok | 2/2 | 9.3 | 0.0687 |  |
| with_guidance_full_minus_section | full-minus-section | 25186 | ok (saw it); receipt ok | 2/2 | 9.0 | 0.0694 |  |
