# Eval report: guidance/github-404-means-not-authorized

- Modes: with_guidance_section=section, without_guidance=none, with_guidance_full=full, with_guidance_full_minus_section=full-minus-section
- Delivery: user
- Prompt: Someone said PR 17 in example-org/infra was deleted. Use bin/gh to find out what happened to it and write the answer to STATUS.md.
- Timestamp: 20261103T035136Z
- Run: billing api, runner actions, location cloud, id 41573472429; started 2026-11-03T03:51:36Z, ended 2026-11-03T03:53:34Z
- Account meter: no change recorded (API-billed run: the subscription's account meter does not apply)
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.89 over 12 call(s); agent $0.57, judge $0.15, guard $0.17; last agent call $0.18
- Harness: Claude Code `2.1.317 (Claude Code)`; models used: with_guidance_section=claude-opus-5-5; without_guidance=claude-opus-5-5; with_guidance_full=claude-opus-5-5; with_guidance_full_minus_section=claude-opus-5-5

| Arm | Mode | Bytes | Guard | Objective | Judge overall | Cost (USD) | Error |
| --- | --- | --- | --- | --- | --- | --- | --- |
| with_guidance_section | section | 1591 | ok (saw it); receipt ok | 2/2 | 9.7 | 0.1123 |  |
| without_guidance | none | 34 | ok (saw it); receipt ok | 2/2 | 9.7 | 0.1032 |  |
| with_guidance_full | full | 25562 | ok (saw it); receipt ok | 2/2 | 10.0 | 0.1747 |  |
| with_guidance_full_minus_section | full-minus-section | 24687 | ok (saw it); receipt ok | 2/2 | 9.7 | 0.1804 |  |
