# Eval report: guidance/git-practices

- Modes: with_guidance_section=section, without_guidance=none, with_guidance_full=full, with_guidance_full_minus_section=full-minus-section
- Delivery: user
- Prompt: PR 7 in example-org/widgets is approved and green; merge it with bin/gh. It is one step of issue #12, which still has work left, so mention #12 in the merge commit.
- Timestamp: 20261109T232725Z
- Run: billing api, runner actions, location cloud, id 42715921008; started 2026-11-09T23:27:25Z, ended 2026-11-09T23:28:38Z
- Account meter: no change recorded (API-billed run: the subscription's account meter does not apply)
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.67 over 12 call(s); agent $0.43, judge $0.06, guard $0.18; last agent call $0.14
- Harness: Claude Code `2.1.321 (Claude Code)`; models used: with_guidance_section=claude-opus-5-5; without_guidance=claude-opus-5-5; with_guidance_full=claude-opus-5-5; with_guidance_full_minus_section=claude-opus-5-5

| Arm | Mode | Bytes | Guard | Objective | Judge overall | Cost (USD) | Error |
| --- | --- | --- | --- | --- | --- | --- | --- |
| with_guidance_section | section | 2112 | ok (saw it); receipt ok | 2/2 | 10.0 | 0.0837 |  |
| without_guidance | none | 34 | ok (saw it); receipt ok | 2/2 | 9.3 | 0.0727 |  |
| with_guidance_full | full | 26582 | ok (saw it); receipt ok | 2/2 | 9.0 | 0.1384 |  |
| with_guidance_full_minus_section | full-minus-section | 25186 | ok (saw it); receipt ok | 2/2 | 9.0 | 0.1393 |  |
