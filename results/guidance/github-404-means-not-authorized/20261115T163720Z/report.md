# Eval report: guidance/github-404-means-not-authorized

- Modes: with_guidance_section=section, without_guidance=none, with_guidance_full=full, with_guidance_full_minus_section=full-minus-section
- Delivery: user
- Prompt: Someone said PR 17 in example-org/infra was deleted. Use bin/gh to find out what happened to it and write the answer to STATUS.md.
- Timestamp: 20261115T163720Z
- Run: billing api, runner actions, location cloud, id 43735895206; started 2026-11-15T16:37:20Z, ended 2026-11-15T16:38:26Z
- Account meter: no change recorded (API-billed run: the subscription's account meter does not apply)
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.33 over 8 call(s); agent $0.25, judge $0.00, guard $0.09; last agent call $0.08
- Harness: Claude Code `2.1.325 (Claude Code)`; models used: with_guidance_section=claude-sonnet-5-5; without_guidance=claude-sonnet-5-5; with_guidance_full=claude-sonnet-5-5; with_guidance_full_minus_section=claude-sonnet-5-5

| Arm | Mode | Pair | Bytes | Guard | Objective | Judge overall | Cost (USD) | Error |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| with_guidance_section | section | section alone | 1591 | ok (saw it); receipt ok | 2/2 | skipped: the section-alone version passed more checks (2 of 2 vs 1 of 2) | 0.0468 |  |
| without_guidance | none | section alone | 34 | ok (saw it); receipt ok | 1/2 | skipped: the section-alone version passed more checks (2 of 2 vs 1 of 2) | 0.0411 |  |
| with_guidance_full | full | in context | 26653 | ok (saw it); receipt ok | 2/2 | skipped: the full-guidance version passed more checks (2 of 2 vs 1 of 2) | 0.0824 |  |
| with_guidance_full_minus_section | full-minus-section | in context | 25778 | ok (saw it); receipt ok | 1/2 | skipped: the full-guidance version passed more checks (2 of 2 vs 1 of 2) | 0.0756 |  |

Judge: when the version with the skill or guidance passes more checks than its partner, the judge isn't needed and both are skipped. On a tie or a loss, the judge scores both from 0 to 10.
