# Eval report: guidance/finding-your-unknowns

- Modes: with_guidance_section=section, without_guidance=none, with_guidance_full=full, with_guidance_full_minus_section=full-minus-section
- Delivery: user
- Prompt: Make sure future agents working in this repo know this: the shared staging database is reset every Sunday from 2:00 to 2:30 AM Eastern, so integration test failures in that window are expected and not worth chasing.
- Timestamp: 20261109T190354Z
- Run: billing api, runner actions, location cloud, id 42676372416; started 2026-11-09T19:03:54Z, ended 2026-11-09T19:05:00Z
- Account meter: no change recorded (API-billed run: the subscription's account meter does not apply)
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.66 over 12 call(s); agent $0.42, judge $0.06, guard $0.18; last agent call $0.13
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_guidance_section=claude-opus-5-5; without_guidance=claude-opus-5-5; with_guidance_full=claude-opus-5-5; with_guidance_full_minus_section=claude-opus-5-5

| Arm | Mode | Bytes | Guard | Objective | Judge overall | Cost (USD) | Error |
| --- | --- | --- | --- | --- | --- | --- | --- |
| with_guidance_section | section | 1731 | ok (saw it); receipt ok | 2/2 | 10.0 | 0.0675 |  |
| without_guidance | none | 34 | ok (saw it); receipt ok | 2/2 | 10.0 | 0.0704 |  |
| with_guidance_full | full | 26582 | ok (saw it); receipt ok | 2/2 | 10.0 | 0.1475 |  |
| with_guidance_full_minus_section | full-minus-section | 25567 | ok (saw it); receipt ok | 2/2 | 10.0 | 0.1302 |  |
