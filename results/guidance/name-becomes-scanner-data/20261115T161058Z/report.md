# Eval report: guidance/name-becomes-scanner-data

- Modes: with_guidance_section=section, without_guidance=none, with_guidance_full=full, with_guidance_full_minus_section=full-minus-section
- Delivery: user
- Prompt: bundles/new-bundle/ holds a helper that provisions the site's deploy secrets. Pin it in bundles.lock with scripts/lock.py, under a short name that says what it is.
- Timestamp: 20261115T161058Z
- Run: billing api, runner actions, location cloud, id 43733816093; started 2026-11-15T16:10:58Z, ended 2026-11-15T16:11:52Z
- Account meter: no change recorded (API-billed run: the subscription's account meter does not apply)
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.32 over 8 call(s); agent $0.21, judge $0.00, guard $0.11; last agent call $0.07
- Harness: Claude Code `2.1.325 (Claude Code)`; models used: with_guidance_section=claude-sonnet-5-5; without_guidance=claude-sonnet-5-5; with_guidance_full=claude-sonnet-5-5; with_guidance_full_minus_section=claude-sonnet-5-5

| Arm | Mode | Pair | Bytes | Guard | Objective | Judge overall | Cost (USD) | Error |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| with_guidance_section | section | section alone | 1719 | ok (saw it); receipt ok | 3/3 | skipped: the section-alone version passed more checks (3 of 3 vs 2 of 3) | 0.0391 |  |
| without_guidance | none | section alone | 34 | ok (saw it); receipt ok | 2/3 | skipped: the section-alone version passed more checks (3 of 3 vs 2 of 3) | 0.0376 |  |
| with_guidance_full | full | in context | 26653 | ok (saw it); receipt ok | 3/3 | skipped: the full-guidance version passed more checks (3 of 3 vs 2 of 3) | 0.0648 |  |
| with_guidance_full_minus_section | full-minus-section | in context | 25650 | ok (saw it); receipt ok | 2/3 | skipped: the full-guidance version passed more checks (3 of 3 vs 2 of 3) | 0.0708 |  |

Judge: when the version with the skill or guidance passes more checks than its partner, the judge isn't needed and both are skipped. On a tie or a loss, the judge scores both from 0 to 10.
