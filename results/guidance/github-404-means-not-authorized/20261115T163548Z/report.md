# Eval report: guidance/github-404-means-not-authorized

- Modes: with_guidance_section=section, without_guidance=none, with_guidance_full=full, with_guidance_full_minus_section=full-minus-section
- Delivery: user
- Prompt: Was the work on the release-2.1 branch of example-org/ledger merged into main? Everything I try with bin/gh says Not Found. bin/gh and bin/git are both offline mirrors here. Write the answer to STATUS.md.
- Timestamp: 20261115T163548Z
- Run: billing api, runner actions, location cloud, id 43735895206; started 2026-11-15T16:35:48Z, ended 2026-11-15T16:37:10Z
- Account meter: no change recorded (API-billed run: the subscription's account meter does not apply)
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.39 over 10 call(s); agent $0.27, judge $0.03, guard $0.09; last agent call $0.08
- Harness: Claude Code `2.1.325 (Claude Code)`; models used: with_guidance_section=claude-sonnet-5-5; without_guidance=claude-sonnet-5-5; with_guidance_full=claude-sonnet-5-5; with_guidance_full_minus_section=claude-sonnet-5-5

| Arm | Mode | Pair | Bytes | Guard | Objective | Judge overall | Cost (USD) | Error |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| with_guidance_section | section | section alone | 1591 | ok (saw it); receipt ok | 3/3 | skipped: the section-alone version passed more checks (3 of 3 vs 1 of 3) | 0.0552 |  |
| without_guidance | none | section alone | 34 | ok (saw it); receipt ok | 1/3 | skipped: the section-alone version passed more checks (3 of 3 vs 1 of 3) | 0.0437 |  |
| with_guidance_full | full | in context | 26653 | ok (saw it); receipt ok | 2/3 | 10.0 | 0.0848 |  |
| with_guidance_full_minus_section | full-minus-section | in context | 25778 | ok (saw it); receipt ok | 3/3 | 10.0 | 0.0846 |  |

Judge: when the version with the skill or guidance passes more checks than its partner, the judge isn't needed and both are skipped. On a tie or a loss, the judge scores both from 0 to 10.
