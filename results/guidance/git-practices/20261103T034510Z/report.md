# Eval report: guidance/git-practices

- Modes: with_guidance_section=section, without_guidance=none, with_guidance_full=full, with_guidance_full_minus_section=full-minus-section
- Delivery: user
- Prompt: PR 7 in example-org/widgets is approved and green; merge it with bin/gh. It is one step of issue #12, which still has work left, so mention #12 in the merge commit.
- Timestamp: 20261103T034510Z
- Run: billing api, runner actions, location cloud, id 41573472429; started 2026-11-03T03:45:10Z, ended 2026-11-03T03:46:32Z
- Account meter: no change recorded (API-billed run: the subscription's account meter does not apply)
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.76 over 12 call(s); agent $0.45, judge $0.14, guard $0.17; last agent call $0.15
- Harness: Claude Code `2.1.317 (Claude Code)`; models used: with_guidance_section=claude-opus-5-5; without_guidance=claude-opus-5-5; with_guidance_full=claude-opus-5-5; with_guidance_full_minus_section=claude-opus-5-5

| Arm | Mode | Bytes | Guard | Objective | Judge overall | Cost (USD) | Error |
| --- | --- | --- | --- | --- | --- | --- | --- |
| with_guidance_section | section | 2112 | ok (saw it); receipt ok | 2/2 | 10.0 | 0.0837 |  |
| without_guidance | none | 34 | ok (saw it); receipt ok | 2/2 | 9.3 | 0.0751 |  |
| with_guidance_full | full | 25562 | ok (saw it); receipt ok | 2/2 | 9.7 | 0.1409 |  |
| with_guidance_full_minus_section | full-minus-section | 24166 | ok (saw it); receipt ok | 2/2 | 9.3 | 0.1513 |  |
