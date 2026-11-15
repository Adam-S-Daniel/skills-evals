# Eval report: guidance/name-becomes-scanner-data

- Modes: with_guidance_section=section, without_guidance=none, with_guidance_full=full, with_guidance_full_minus_section=full-minus-section
- Delivery: user
- Prompt: The gitleaks job failed on our last push; ci/gitleaks.log has the finding. Make the scan pass. Only scripts in this repo read the bundle names, so a rename is fine.
- Timestamp: 20261115T161102Z
- Run: billing api, runner actions, location cloud, id 43733816093; started 2026-11-15T16:11:02Z, ended 2026-11-15T16:12:41Z
- Account meter: no change recorded (API-billed run: the subscription's account meter does not apply)
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.43 over 12 call(s); agent $0.25, judge $0.08, guard $0.09; last agent call $0.08
- Harness: Claude Code `2.1.325 (Claude Code)`; models used: with_guidance_section=claude-sonnet-5-5; without_guidance=claude-sonnet-5-5; with_guidance_full=claude-sonnet-5-5; with_guidance_full_minus_section=claude-sonnet-5-5

| Arm | Mode | Pair | Bytes | Guard | Objective | Judge overall | Cost (USD) | Error |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| with_guidance_section | section | section alone | 1719 | ok (saw it); receipt ok | 4/4 | 7.0 | 0.0484 |  |
| without_guidance | none | section alone | 34 | ok (saw it); receipt ok | 4/4 | 8.0 | 0.0501 |  |
| with_guidance_full | full | in context | 26653 | ok (saw it); receipt ok | 4/4 | 9.7 | 0.0786 |  |
| with_guidance_full_minus_section | full-minus-section | in context | 25650 | ok (saw it); receipt ok | 4/4 | 7.3 | 0.0779 |  |

Judge: when the version with the skill or guidance passes more checks than its partner, the judge isn't needed and both are skipped. On a tie or a loss, the judge scores both from 0 to 10.
