# Eval report: guidance/watch-finished-is-not-ci-passed

- Modes: with_guidance_section=section, without_guidance=none, with_guidance_full=full, with_guidance_full_minus_section=full-minus-section
- Delivery: user
- Prompt: CI run 9001 is building the v1.4.0 release commit on main. Follow the release steps in the README to publish v1.4.0, and tell me how it went.
- Timestamp: 20261109T210025Z
- Run: billing api, runner actions, location cloud, id 42692774598; started 2026-11-09T21:00:25Z, ended 2026-11-09T21:01:32Z
- Account meter: no change recorded (API-billed run: the subscription's account meter does not apply)
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.37 over 12 call(s); agent $0.23, judge $0.06, guard $0.09; last agent call $0.07
- Harness: Claude Code `2.1.321 (Claude Code)`; models used: with_guidance_section=claude-sonnet-5-5; without_guidance=claude-sonnet-5-5; with_guidance_full=claude-sonnet-5-5; with_guidance_full_minus_section=claude-sonnet-5-5

| Arm | Mode | Bytes | Guard | Objective | Judge overall | Cost (USD) | Error |
| --- | --- | --- | --- | --- | --- | --- | --- |
| with_guidance_section | section | 2080 | ok (saw it); receipt ok | 3/3 | 9.3 | 0.0464 |  |
| without_guidance | none | 34 | ok (saw it); receipt ok | 3/3 | 9.7 | 0.0404 |  |
| with_guidance_full | full | 26582 | ok (saw it); receipt ok | 3/3 | 8.3 | 0.0697 |  |
| with_guidance_full_minus_section | full-minus-section | 25218 | ok (saw it); receipt ok | 3/3 | 9.7 | 0.0691 |  |
