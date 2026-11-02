# Eval report: guidance/watch-finished-is-not-ci-passed

- Modes: with_guidance_section=section, without_guidance=none, with_guidance_full=full, with_guidance_full_minus_section=full-minus-section
- Delivery: user
- Prompt: PR 42 in example-org/widgets is waiting on CI. Use bin/gh to wait for CI to finish. If everything passed, merge it. If not, leave it unmerged and write what is failing to CI-STATUS.md.
- Timestamp: 20261102T231100Z
- Run: billing api, runner actions, location cloud, id 41542886876; started 2026-11-02T23:11:00Z, ended 2026-11-02T23:11:53Z
- Account meter: no change recorded (API-billed run: the subscription's account meter does not apply)
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.31 over 8 call(s); agent $0.22, judge $0.00, guard $0.09; last agent call $0.07
- Harness: Claude Code `2.1.316 (Claude Code)`; models used: with_guidance_section=claude-sonnet-5-5; without_guidance=claude-sonnet-5-5; with_guidance_full=claude-sonnet-5-5; with_guidance_full_minus_section=claude-sonnet-5-5

| Arm | Mode | Bytes | Guard | Objective | Judge overall | Cost (USD) | Error |
| --- | --- | --- | --- | --- | --- | --- | --- |
| with_guidance_section | section | 2080 | ok (saw it); receipt ok | 2/2 | skipped (objective-decided) | 0.0474 |  |
| without_guidance | none | 34 | ok (saw it); receipt ok | 0/2 | skipped (objective-decided) | 0.0316 |  |
| with_guidance_full | full | 25562 | ok (saw it); receipt ok | 2/2 | skipped (objective-decided) | 0.0745 |  |
| with_guidance_full_minus_section | full-minus-section | 24198 | ok (saw it); receipt ok | 0/2 | skipped (objective-decided) | 0.0710 |  |
