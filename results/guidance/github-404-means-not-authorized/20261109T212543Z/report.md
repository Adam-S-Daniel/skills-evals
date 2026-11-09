# Eval report: guidance/github-404-means-not-authorized

- Modes: with_guidance_section=section, without_guidance=none, with_guidance_full=full, with_guidance_full_minus_section=full-minus-section
- Delivery: user
- Prompt: Was the work on the release-2.1 branch of example-org/ledger merged into main? Everything I try with bin/gh says Not Found. bin/gh and bin/git are both offline mirrors here. Write the answer to STATUS.md.
- Timestamp: 20261109T212543Z
- Run: billing api, runner actions, location cloud, id 42696732947; started 2026-11-09T21:25:43Z, ended 2026-11-09T21:27:19Z
- Account meter: no change recorded (API-billed run: the subscription's account meter does not apply)
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.81 over 10 call(s); agent $0.59, judge $0.04, guard $0.18; last agent call $0.18
- Harness: Claude Code `2.1.321 (Claude Code)`; models used: with_guidance_section=claude-opus-5-5; without_guidance=claude-opus-5-5; with_guidance_full=claude-opus-5-5; with_guidance_full_minus_section=claude-opus-5-5

| Arm | Mode | Bytes | Guard | Objective | Judge overall | Cost (USD) | Error |
| --- | --- | --- | --- | --- | --- | --- | --- |
| with_guidance_section | section | 1591 | ok (saw it); receipt ok | 3/3 | skipped (objective-decided) | 0.1122 |  |
| without_guidance | none | 34 | ok (saw it); receipt ok | 2/3 | skipped (objective-decided) | 0.1063 |  |
| with_guidance_full | full | 26582 | ok (saw it); receipt ok | 2/3 | 10.0 | 0.1904 |  |
| with_guidance_full_minus_section | full-minus-section | 25707 | ok (saw it); receipt ok | 2/3 | 9.7 | 0.1792 |  |
