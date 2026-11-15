# Eval report: guidance/finding-your-unknowns

- Modes: with_guidance_section=section, without_guidance=none, with_guidance_full=full, with_guidance_full_minus_section=full-minus-section
- Delivery: user
- Prompt: Make sure future agents working in this repo know this: the shared staging database is reset every Sunday from 2:00 to 2:30 AM Eastern, so integration test failures in that window are expected and not worth chasing.
- Timestamp: 20261115T163552Z
- Run: billing api, runner actions, location cloud, id 43735895206; started 2026-11-15T16:35:52Z, ended 2026-11-15T16:37:02Z
- Account meter: no change recorded (API-billed run: the subscription's account meter does not apply)
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.34 over 12 call(s); agent $0.20, judge $0.05, guard $0.09; last agent call $0.06
- Harness: Claude Code `2.1.325 (Claude Code)`; models used: with_guidance_section=claude-sonnet-5-5; without_guidance=claude-sonnet-5-5; with_guidance_full=claude-sonnet-5-5; with_guidance_full_minus_section=claude-sonnet-5-5

| Arm | Mode | Pair | Bytes | Guard | Objective | Judge overall | Cost (USD) | Error |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| with_guidance_section | section | section alone | 1731 | ok (saw it); receipt ok | 2/2 | 10.0 | 0.0367 |  |
| without_guidance | none | section alone | 34 | ok (saw it); receipt ok | 2/2 | 9.7 | 0.0339 |  |
| with_guidance_full | full | in context | 26653 | ok (saw it); receipt ok | 2/2 | 10.0 | 0.0640 |  |
| with_guidance_full_minus_section | full-minus-section | in context | 25638 | ok (saw it); receipt ok | 2/2 | 10.0 | 0.0609 |  |

Judge: when the version with the skill or guidance passes more checks than its partner, the judge isn't needed and both are skipped. On a tie or a loss, the judge scores both from 0 to 10.
