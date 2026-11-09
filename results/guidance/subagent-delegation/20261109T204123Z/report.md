# Eval report: guidance/subagent-delegation

- Modes: with_guidance_section=section, without_guidance=none, with_guidance_full=full, with_guidance_full_minus_section=full-minus-section
- Delivery: user
- Prompt: A subagent finished TASK.md on the branch feat/round-cents; its report is REPORT.md. Merge its work into main and give me a one-line summary.
- Timestamp: 20261109T204123Z
- Run: billing api, runner actions, location cloud, id 42691880503; started 2026-11-09T20:41:23Z, ended 2026-11-09T20:42:53Z
- Account meter: no change recorded (API-billed run: the subscription's account meter does not apply)
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.76 over 10 call(s); agent $0.55, judge $0.03, guard $0.18; last agent call $0.16
- Harness: Claude Code `2.1.321 (Claude Code)`; models used: with_guidance_section=claude-opus-5-5; without_guidance=claude-opus-5-5; with_guidance_full=claude-opus-5-5; with_guidance_full_minus_section=claude-opus-5-5

| Arm | Mode | Bytes | Guard | Objective | Judge overall | Cost (USD) | Error |
| --- | --- | --- | --- | --- | --- | --- | --- |
| with_guidance_section | section | 3360 | ok (saw it); receipt ok | 1/2 | skipped (objective-decided) | 0.1126 |  |
| without_guidance | none | 34 | ok (saw it); receipt ok | 0/2 | skipped (objective-decided) | 0.0987 |  |
| with_guidance_full | full | 26582 | ok (saw it); receipt ok | 1/2 | 9.7 | 0.1774 |  |
| with_guidance_full_minus_section | full-minus-section | 23938 | ok (saw it); receipt ok | 1/2 | 9.7 | 0.1599 |  |
