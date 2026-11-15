# Eval report: guidance/fleet-spans-two-owners

- Modes: with_guidance_section=section, without_guidance=none, with_guidance_full=full, with_guidance_full_minus_section=full-minus-section
- Delivery: user
- Prompt: Which repositories in the fleet have no skills.lock at their root? Write them to MISSING.md, one owner/name per line and nothing else, and tell me how you checked.
- Timestamp: 20261115T162148Z
- Run: billing api, runner actions, location cloud, id 43733816093; started 2026-11-15T16:21:48Z, ended 2026-11-15T16:23:11Z
- Account meter: no change recorded (API-billed run: the subscription's account meter does not apply)
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.41 over 12 call(s); agent $0.27, judge $0.05, guard $0.09; last agent call $0.09
- Harness: Claude Code `2.1.325 (Claude Code)`; models used: with_guidance_section=claude-sonnet-5-5; without_guidance=claude-sonnet-5-5; with_guidance_full=claude-sonnet-5-5; with_guidance_full_minus_section=claude-sonnet-5-5

| Arm | Mode | Pair | Bytes | Guard | Objective | Judge overall | Cost (USD) | Error |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| with_guidance_section | section | section alone | 1679 | ok (saw it); receipt ok | 2/3 | 10.0 | 0.0517 |  |
| without_guidance | none | section alone | 34 | ok (saw it); receipt ok | 3/3 | 10.0 | 0.0481 |  |
| with_guidance_full | full | in context | 26653 | ok (saw it); receipt ok | 2/3 | 10.0 | 0.0788 |  |
| with_guidance_full_minus_section | full-minus-section | in context | 25690 | ok (saw it); receipt ok | 2/3 | 10.0 | 0.0887 |  |

Judge: when the version with the skill or guidance passes more checks than its partner, the judge isn't needed and both are skipped. On a tie or a loss, the judge scores both from 0 to 10.
