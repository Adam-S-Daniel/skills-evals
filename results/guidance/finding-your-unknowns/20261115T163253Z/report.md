# Eval report: guidance/finding-your-unknowns

- Modes: with_guidance_section=section, without_guidance=none, with_guidance_full=full, with_guidance_full_minus_section=full-minus-section
- Delivery: user
- Prompt: Agents in several of our repos keep committing shell scripts with Windows (CRLF) line endings, and the scripts then break on the Linux runners. Make that stop across the fleet.
- Timestamp: 20261115T163253Z
- Run: billing api, runner actions, location cloud, id 43735895206; started 2026-11-15T16:32:53Z, ended 2026-11-15T16:35:01Z
- Account meter: no change recorded (API-billed run: the subscription's account meter does not apply)
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.53 over 12 call(s); agent $0.33, judge $0.11, guard $0.09; last agent call $0.12
- Harness: Claude Code `2.1.325 (Claude Code)`; models used: with_guidance_section=claude-sonnet-5-5; without_guidance=claude-sonnet-5-5; with_guidance_full=claude-sonnet-5-5; with_guidance_full_minus_section=claude-sonnet-5-5

| Arm | Mode | Pair | Bytes | Guard | Objective | Judge overall | Cost (USD) | Error |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| with_guidance_section | section | section alone | 1731 | ok (saw it); receipt ok | 1/1 | 9.7 | 0.0549 |  |
| without_guidance | none | section alone | 34 | ok (saw it); receipt ok | 1/1 | 9.0 | 0.0589 |  |
| with_guidance_full | full | in context | 26653 | ok (saw it); receipt ok | 1/1 | 9.0 | 0.0984 |  |
| with_guidance_full_minus_section | full-minus-section | in context | 25638 | ok (saw it); receipt ok | 1/1 | 9.0 | 0.1178 |  |

Judge: when the version with the skill or guidance passes more checks than its partner, the judge isn't needed and both are skipped. On a tie or a loss, the judge scores both from 0 to 10.
