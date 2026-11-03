# Eval report: guidance/git-practices

- Modes: with_guidance_section=section, without_guidance=none, with_guidance_full=full, with_guidance_full_minus_section=full-minus-section
- Delivery: user
- Prompt: PR 7 in example-org/widgets is approved and green; merge it with bin/gh. It is one step of issue #12, which still has work left, so mention #12 in the merge commit.
- Timestamp: 20261103T061228Z
- Run: billing api, runner actions, location cloud, id 41587675812; started 2026-11-03T06:12:28Z, ended 2026-11-03T06:13:50Z
- Account meter: no change recorded (API-billed run: the subscription's account meter does not apply)
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.75 over 12 call(s); agent $0.44, judge $0.13, guard $0.17; last agent call $0.14
- Harness: Claude Code `2.1.317 (Claude Code)`; models used: with_guidance_section=claude-opus-5-5; without_guidance=claude-opus-5-5; with_guidance_full=claude-opus-5-5; with_guidance_full_minus_section=claude-opus-5-5

| Arm | Mode | Bytes | Guard | Objective | Judge overall | Cost (USD) | Error |
| --- | --- | --- | --- | --- | --- | --- | --- |
| with_guidance_section | section | 2112 | ok (saw it); receipt ok | 2/2 | 10.0 | 0.0803 |  |
| without_guidance | none | 34 | ok (saw it); receipt ok | 2/2 | 8.7 | 0.0751 |  |
| with_guidance_full | full | 25562 | ok (saw it); receipt ok | 2/2 | 10.0 | 0.1467 |  |
| with_guidance_full_minus_section | full-minus-section | 24166 | ok (saw it); receipt ok | 2/2 | 9.3 | 0.1388 |  |
