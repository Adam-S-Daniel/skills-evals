# Eval report: guidance/subagent-delegation

- Modes: with_guidance_section=section, without_guidance=none, with_guidance_full=full, with_guidance_full_minus_section=full-minus-section
- Delivery: user
- Prompt: I want to hand TASK.md to a subagent and not look at it again until it reports. Do not do the rename yourself. Write the complete prompt you would give the subagent, plus the settings you would delegate it with, to HANDOFF.md.
- Timestamp: 20261115T161521Z
- Run: billing api, runner actions, location cloud, id 43733816093; started 2026-11-15T16:15:21Z, ended 2026-11-15T16:17:15Z
- Account meter: no change recorded (API-billed run: the subscription's account meter does not apply)
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.41 over 8 call(s); agent $0.32, judge $0.00, guard $0.09; last agent call $0.08
- Harness: Claude Code `2.1.325 (Claude Code)`; models used: with_guidance_section=claude-sonnet-5-5; without_guidance=claude-sonnet-5-5; with_guidance_full=claude-sonnet-5-5; with_guidance_full_minus_section=claude-sonnet-5-5

| Arm | Mode | Pair | Bytes | Guard | Objective | Judge overall | Cost (USD) | Error |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| with_guidance_section | section | section alone | 3360 | ok (saw it); receipt ok | 3/3 | skipped: the section-alone version passed more checks (3 of 3 vs 2 of 3) | 0.0727 |  |
| without_guidance | none | section alone | 34 | ok (saw it); receipt ok | 2/3 | skipped: the section-alone version passed more checks (3 of 3 vs 2 of 3) | 0.0724 |  |
| with_guidance_full | full | in context | 26653 | ok (saw it); receipt ok | 3/3 | skipped: the full-guidance version passed more checks (3 of 3 vs 2 of 3) | 0.0922 |  |
| with_guidance_full_minus_section | full-minus-section | in context | 24009 | ok (saw it); receipt ok | 2/3 | skipped: the full-guidance version passed more checks (3 of 3 vs 2 of 3) | 0.0803 |  |

Judge: when the version with the skill or guidance passes more checks than its partner, the judge isn't needed and both are skipped. On a tie or a loss, the judge scores both from 0 to 10.
