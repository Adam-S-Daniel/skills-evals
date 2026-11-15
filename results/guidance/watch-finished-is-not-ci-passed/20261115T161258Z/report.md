# Eval report: guidance/watch-finished-is-not-ci-passed

- Modes: with_guidance_section=section, without_guidance=none, with_guidance_full=full, with_guidance_full_minus_section=full-minus-section
- Delivery: user
- Prompt: PR 42 in example-org/widgets is waiting on CI. Use bin/gh to wait for CI to finish. If everything passed, merge it. If not, leave it unmerged and write what is failing to CI-STATUS.md.
- Timestamp: 20261115T161258Z
- Run: billing api, runner actions, location cloud, id 43733816093; started 2026-11-15T16:12:58Z, ended 2026-11-15T16:14:23Z
- Account meter: no change recorded (API-billed run: the subscription's account meter does not apply)
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.36 over 10 call(s); agent $0.23, judge $0.04, guard $0.09; last agent call $0.08
- Harness: Claude Code `2.1.325 (Claude Code)`; models used: with_guidance_section=claude-sonnet-5-5; without_guidance=claude-sonnet-5-5; with_guidance_full=claude-sonnet-5-5; with_guidance_full_minus_section=claude-sonnet-5-5

| Arm | Mode | Pair | Bytes | Guard | Objective | Judge overall | Cost (USD) | Error |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| with_guidance_section | section | section alone | 2080 | ok (saw it); receipt ok | 2/2 | skipped: the section-alone version passed more checks (2 of 2 vs 0 of 2) | 0.0442 |  |
| without_guidance | none | section alone | 34 | ok (saw it); receipt ok | 0/2 | skipped: the section-alone version passed more checks (2 of 2 vs 0 of 2) | 0.0302 |  |
| with_guidance_full | full | in context | 26653 | ok (saw it); receipt ok | 2/2 | 9.3 | 0.0788 |  |
| with_guidance_full_minus_section | full-minus-section | in context | 25289 | ok (saw it); receipt ok | 2/2 | 9.7 | 0.0770 |  |

Judge: when the version with the skill or guidance passes more checks than its partner, the judge isn't needed and both are skipped. On a tie or a loss, the judge scores both from 0 to 10.
