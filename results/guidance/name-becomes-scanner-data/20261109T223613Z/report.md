# Eval report: guidance/name-becomes-scanner-data

- Modes: with_guidance_section=section, without_guidance=none, with_guidance_full=full, with_guidance_full_minus_section=full-minus-section
- Delivery: user
- Prompt: bundles/new-bundle/ holds a helper that provisions the site's deploy secrets. Pin it in bundles.lock with scripts/lock.py, under a short name that says what it is.
- Timestamp: 20261109T223613Z
- Run: billing api, runner actions, location cloud, id 42709867070; started 2026-11-09T22:36:13Z, ended 2026-11-09T22:37:46Z
- Account meter: no change recorded (API-billed run: the subscription's account meter does not apply)
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.73 over 12 call(s); agent $0.49, judge $0.06, guard $0.18; last agent call $0.16
- Harness: Claude Code `2.1.321 (Claude Code)`; models used: with_guidance_section=claude-opus-5-5; without_guidance=claude-opus-5-5; with_guidance_full=claude-opus-5-5; with_guidance_full_minus_section=claude-opus-5-5

| Arm | Mode | Bytes | Guard | Objective | Judge overall | Cost (USD) | Error |
| --- | --- | --- | --- | --- | --- | --- | --- |
| with_guidance_section | section | 1719 | ok (saw it); receipt ok | 3/3 | 8.0 | 0.0809 |  |
| without_guidance | none | 34 | ok (saw it); receipt ok | 3/3 | 9.0 | 0.0994 |  |
| with_guidance_full | full | 26582 | ok (saw it); receipt ok | 3/3 | 9.7 | 0.1519 |  |
| with_guidance_full_minus_section | full-minus-section | 25579 | ok (saw it); receipt ok | 3/3 | 9.7 | 0.1600 |  |
