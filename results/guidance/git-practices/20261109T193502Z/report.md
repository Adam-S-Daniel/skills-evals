# Eval report: guidance/git-practices

- Modes: with_guidance_section=section, without_guidance=none, with_guidance_full=full, with_guidance_full_minus_section=full-minus-section
- Delivery: user
- Prompt: PR 7 in example-org/widgets is approved and green; merge it with bin/gh. It is one step of issue #12, which still has work left, so mention #12 in the merge commit.
- Timestamp: 20261109T193502Z
- Run: billing api, runner actions, location cloud, id 42680911395; started 2026-11-09T19:35:02Z, ended 2026-11-09T19:36:08Z
- Account meter: no change recorded (API-billed run: the subscription's account meter does not apply)
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.37 over 12 call(s); agent $0.22, judge $0.07, guard $0.09; last agent call $0.07
- Harness: Claude Code `2.1.321 (Claude Code)`; models used: with_guidance_section=claude-sonnet-5-5; without_guidance=claude-sonnet-5-5; with_guidance_full=claude-sonnet-5-5; with_guidance_full_minus_section=claude-sonnet-5-5

| Arm | Mode | Bytes | Guard | Objective | Judge overall | Cost (USD) | Error |
| --- | --- | --- | --- | --- | --- | --- | --- |
| with_guidance_section | section | 2112 | ok (saw it); receipt ok | 2/2 | 9.3 | 0.0371 |  |
| without_guidance | none | 34 | ok (saw it); receipt ok | 2/2 | 9.0 | 0.0359 |  |
| with_guidance_full | full | 26582 | ok (saw it); receipt ok | 2/2 | 9.7 | 0.0697 |  |
| with_guidance_full_minus_section | full-minus-section | 25186 | ok (saw it); receipt ok | 2/2 | 8.7 | 0.0744 |  |
