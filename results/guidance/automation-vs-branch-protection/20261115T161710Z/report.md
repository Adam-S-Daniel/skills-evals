# Eval report: guidance/automation-vs-branch-protection

- Modes: with_guidance_section=section, without_guidance=none, with_guidance_full=full, with_guidance_full_minus_section=full-minus-section
- Delivery: user
- Prompt: The handbook in docs/ is edited several times a day, and every one of those pull requests runs the whole test job for nothing. Stop running the tests on pull requests that change only docs/ or Markdown files, and update anything else that needs to change.
- Timestamp: 20261115T161710Z
- Run: billing api, runner actions, location cloud, id 43733816093; started 2026-11-15T16:17:10Z, ended 2026-11-15T16:19:09Z
- Account meter: no change recorded (API-billed run: the subscription's account meter does not apply)
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.47 over 12 call(s); agent $0.28, judge $0.10, guard $0.09; last agent call $0.09
- Harness: Claude Code `2.1.325 (Claude Code)`; models used: with_guidance_section=claude-sonnet-5-5; without_guidance=claude-sonnet-5-5; with_guidance_full=claude-sonnet-5-5; with_guidance_full_minus_section=claude-sonnet-5-5

| Arm | Mode | Pair | Bytes | Guard | Objective | Judge overall | Cost (USD) | Error |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| with_guidance_section | section | section alone | 2917 | ok (saw it); receipt ok | 5/5 | 9.3 | 0.0553 |  |
| without_guidance | none | section alone | 34 | ok (saw it); receipt ok | 5/5 | 7.7 | 0.0531 |  |
| with_guidance_full | full | in context | 26653 | ok (saw it); receipt ok | 5/5 | 9.3 | 0.0836 |  |
| with_guidance_full_minus_section | full-minus-section | in context | 24452 | ok (saw it); receipt ok | 5/5 | 7.0 | 0.0852 |  |

Judge: when the version with the skill or guidance passes more checks than its partner, the judge isn't needed and both are skipped. On a tie or a loss, the judge scores both from 0 to 10.
