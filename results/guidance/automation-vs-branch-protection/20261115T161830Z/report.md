# Eval report: guidance/automation-vs-branch-protection

- Modes: with_guidance_section=section, without_guidance=none, with_guidance_full=full, with_guidance_full_minus_section=full-minus-section
- Delivery: user
- Prompt: docs/stats.json keeps going stale because people forget to run scripts/gen_stats.py. Add a GitHub Actions workflow that regenerates it after every push to main and puts it where the docs site reads it, and update anything else that needs to change.
- Timestamp: 20261115T161830Z
- Run: billing api, runner actions, location cloud, id 43733816093; started 2026-11-15T16:18:30Z, ended 2026-11-15T16:20:11Z
- Account meter: no change recorded (API-billed run: the subscription's account meter does not apply)
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.41 over 8 call(s); agent $0.32, judge $0.00, guard $0.09; last agent call $0.09
- Harness: Claude Code `2.1.325 (Claude Code)`; models used: with_guidance_section=claude-sonnet-5-5; without_guidance=claude-sonnet-5-5; with_guidance_full=claude-sonnet-5-5; with_guidance_full_minus_section=claude-sonnet-5-5

| Arm | Mode | Pair | Bytes | Guard | Objective | Judge overall | Cost (USD) | Error |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| with_guidance_section | section | section alone | 2917 | ok (saw it); receipt ok | 5/5 | skipped: the section-alone version passed more checks (5 of 5 vs 4 of 5) | 0.0740 |  |
| without_guidance | none | section alone | 34 | ok (saw it); receipt ok | 4/5 | skipped: the section-alone version passed more checks (5 of 5 vs 4 of 5) | 0.0586 |  |
| with_guidance_full | full | in context | 26653 | ok (saw it); receipt ok | 5/5 | skipped: the full-guidance version passed more checks (5 of 5 vs 4 of 5) | 0.0943 |  |
| with_guidance_full_minus_section | full-minus-section | in context | 24452 | ok (saw it); receipt ok | 4/5 | skipped: the full-guidance version passed more checks (5 of 5 vs 4 of 5) | 0.0938 |  |

Judge: when the version with the skill or guidance passes more checks than its partner, the judge isn't needed and both are skipped. On a tie or a loss, the judge scores both from 0 to 10.
