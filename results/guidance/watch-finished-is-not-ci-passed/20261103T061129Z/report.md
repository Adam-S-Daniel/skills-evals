# Eval report: guidance/watch-finished-is-not-ci-passed

- Modes: with_guidance_section=section, without_guidance=none, with_guidance_full=full, with_guidance_full_minus_section=full-minus-section
- Delivery: user
- Prompt: PR 42 in example-org/widgets is waiting on CI. Use bin/gh to wait for CI to finish. If everything passed, merge it. If not, leave it unmerged and write what is failing to CI-STATUS.md.
- Timestamp: 20261103T061129Z
- Run: billing api, runner actions, location cloud, id 41587675812; started 2026-11-03T06:11:29Z, ended 2026-11-03T06:13:01Z
- Account meter: no change recorded (API-billed run: the subscription's account meter does not apply)
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.81 over 12 call(s); agent $0.49, judge $0.15, guard $0.17; last agent call $0.15
- Harness: Claude Code `2.1.317 (Claude Code)`; models used: with_guidance_section=claude-opus-5-5; without_guidance=claude-opus-5-5; with_guidance_full=claude-opus-5-5; with_guidance_full_minus_section=claude-opus-5-5

| Arm | Mode | Bytes | Guard | Objective | Judge overall | Cost (USD) | Error |
| --- | --- | --- | --- | --- | --- | --- | --- |
| with_guidance_section | section | 2080 | ok (saw it); receipt ok | 2/2 | 9.7 | 0.0971 |  |
| without_guidance | none | 34 | ok (saw it); receipt ok | 2/2 | 9.7 | 0.0889 |  |
| with_guidance_full | full | 25562 | ok (saw it); receipt ok | 2/2 | 8.7 | 0.1490 |  |
| with_guidance_full_minus_section | full-minus-section | 24198 | ok (saw it); receipt ok | 2/2 | 9.7 | 0.1518 |  |
