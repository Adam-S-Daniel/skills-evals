# Eval report: guidance/github-404-means-not-authorized

- Modes: with_guidance_section=section, without_guidance=none, with_guidance_full=full, with_guidance_full_minus_section=full-minus-section
- Delivery: user
- Prompt: Was the work on the release-2.1 branch of example-org/ledger merged into main? Everything I try with bin/gh says Not Found. bin/gh and bin/git are both offline mirrors here. Write the answer to STATUS.md.
- Timestamp: 20261109T214644Z
- Run: billing api, runner actions, location cloud, id 42699607181; started 2026-11-09T21:46:44Z, ended 2026-11-09T21:47:59Z
- Account meter: no change recorded (API-billed run: the subscription's account meter does not apply)
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.40 over 10 call(s); agent $0.27, judge $0.04, guard $0.09; last agent call $0.08
- Harness: Claude Code `2.1.321 (Claude Code)`; models used: with_guidance_section=claude-sonnet-5-5; without_guidance=claude-sonnet-5-5; with_guidance_full=claude-sonnet-5-5; with_guidance_full_minus_section=claude-sonnet-5-5

| Arm | Mode | Bytes | Guard | Objective | Judge overall | Cost (USD) | Error |
| --- | --- | --- | --- | --- | --- | --- | --- |
| with_guidance_section | section | 1591 | ok (saw it); receipt ok | 3/3 | skipped (objective-decided) | 0.0488 |  |
| without_guidance | none | 34 | ok (saw it); receipt ok | 2/3 | skipped (objective-decided) | 0.0518 |  |
| with_guidance_full | full | 26582 | ok (saw it); receipt ok | 2/3 | 8.0 | 0.0821 |  |
| with_guidance_full_minus_section | full-minus-section | 25707 | ok (saw it); receipt ok | 3/3 | 10.0 | 0.0846 |  |
