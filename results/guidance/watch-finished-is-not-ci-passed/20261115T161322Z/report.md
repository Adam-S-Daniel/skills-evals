# Eval report: guidance/watch-finished-is-not-ci-passed

- Modes: with_guidance_section=section, without_guidance=none, with_guidance_full=full, with_guidance_full_minus_section=full-minus-section
- Delivery: user
- Prompt: CI run 9001 is building the v1.4.0 release commit on main. Follow the release steps in the README to publish v1.4.0, and tell me how it went.
- Timestamp: 20261115T161322Z
- Run: billing api, runner actions, location cloud, id 43733816093; started 2026-11-15T16:13:22Z, ended 2026-11-15T16:14:29Z
- Account meter: no change recorded (API-billed run: the subscription's account meter does not apply)
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.37 over 12 call(s); agent $0.23, judge $0.06, guard $0.09; last agent call $0.07
- Harness: Claude Code `2.1.325 (Claude Code)`; models used: with_guidance_section=claude-sonnet-5-5; without_guidance=claude-sonnet-5-5; with_guidance_full=claude-sonnet-5-5; with_guidance_full_minus_section=claude-sonnet-5-5

| Arm | Mode | Pair | Bytes | Guard | Objective | Judge overall | Cost (USD) | Error |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| with_guidance_section | section | section alone | 2080 | ok (saw it); receipt ok | 3/3 | 9.3 | 0.0457 |  |
| without_guidance | none | section alone | 34 | ok (saw it); receipt ok | 3/3 | 9.7 | 0.0393 |  |
| with_guidance_full | full | in context | 26653 | ok (saw it); receipt ok | 3/3 | 9.7 | 0.0710 |  |
| with_guidance_full_minus_section | full-minus-section | in context | 25289 | ok (saw it); receipt ok | 3/3 | 9.7 | 0.0706 |  |

Judge: when the version with the skill or guidance passes more checks than its partner, the judge isn't needed and both are skipped. On a tie or a loss, the judge scores both from 0 to 10.
