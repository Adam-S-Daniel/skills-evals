# Eval report: guidance/subagent-delegation

- Modes: with_guidance_section=section, without_guidance=none, with_guidance_full=full, with_guidance_full_minus_section=full-minus-section
- Delivery: user
- Prompt: A subagent finished TASK.md on the branch feat/round-cents; its report is REPORT.md. Merge its work into main and give me a one-line summary.
- Timestamp: 20261115T161339Z
- Run: billing api, runner actions, location cloud, id 43733816093; started 2026-11-15T16:13:39Z, ended 2026-11-15T16:15:06Z
- Account meter: no change recorded (API-billed run: the subscription's account meter does not apply)
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.40 over 12 call(s); agent $0.25, judge $0.06, guard $0.09; last agent call $0.08
- Harness: Claude Code `2.1.325 (Claude Code)`; models used: with_guidance_section=claude-sonnet-5-5; without_guidance=claude-sonnet-5-5; with_guidance_full=claude-sonnet-5-5; with_guidance_full_minus_section=claude-sonnet-5-5

| Arm | Mode | Pair | Bytes | Guard | Objective | Judge overall | Cost (USD) | Error |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| with_guidance_section | section | section alone | 3360 | ok (saw it); receipt ok | 0/2 | 9.7 | 0.0534 |  |
| without_guidance | none | section alone | 34 | ok (saw it); receipt ok | 1/2 | 9.0 | 0.0487 |  |
| with_guidance_full | full | in context | 26653 | ok (saw it); receipt ok | 1/2 | 9.7 | 0.0727 |  |
| with_guidance_full_minus_section | full-minus-section | in context | 24009 | ok (saw it); receipt ok | 1/2 | 9.7 | 0.0786 |  |

Judge: when the version with the skill or guidance passes more checks than its partner, the judge isn't needed and both are skipped. On a tie or a loss, the judge scores both from 0 to 10.
