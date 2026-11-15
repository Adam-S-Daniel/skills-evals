# Eval report: guidance/automation-vs-branch-protection

- Modes: with_guidance_section=section, without_guidance=none, with_guidance_full=full, with_guidance_full_minus_section=full-minus-section
- Delivery: user
- Prompt: Every time someone adds a label to a pull request, ci.yml runs the whole test job again and we pay for the duplicate. Stop the duplicate runs, and keep the e2e label working.
- Timestamp: 20261115T162001Z
- Run: billing api, runner actions, location cloud, id 43733816093; started 2026-11-15T16:20:00Z, ended 2026-11-15T16:21:40Z
- Account meter: no change recorded (API-billed run: the subscription's account meter does not apply)
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.41 over 12 call(s); agent $0.22, judge $0.10, guard $0.09; last agent call $0.07
- Harness: Claude Code `2.1.325 (Claude Code)`; models used: with_guidance_section=claude-sonnet-5-5; without_guidance=claude-sonnet-5-5; with_guidance_full=claude-sonnet-5-5; with_guidance_full_minus_section=claude-sonnet-5-5

| Arm | Mode | Pair | Bytes | Guard | Objective | Judge overall | Cost (USD) | Error |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| with_guidance_section | section | section alone | 2917 | ok (saw it); receipt ok | 3/4 | 8.0 | 0.0433 |  |
| without_guidance | none | section alone | 34 | ok (saw it); receipt ok | 3/4 | 8.3 | 0.0380 |  |
| with_guidance_full | full | in context | 26653 | ok (saw it); receipt ok | 3/4 | 6.5 | 0.0703 |  |
| with_guidance_full_minus_section | full-minus-section | in context | 24452 | ok (saw it); receipt ok | 3/4 | 7.0 | 0.0669 |  |

Judge: when the version with the skill or guidance passes more checks than its partner, the judge isn't needed and both are skipped. On a tie or a loss, the judge scores both from 0 to 10.
