# Eval report: guidance/subagent-delegation

- Modes: with_guidance_section=section, without_guidance=none, with_guidance_full=full, with_guidance_full_minus_section=full-minus-section
- Delivery: user
- Prompt: A subagent finished TASK.md on the branch feat/round-cents; its report is REPORT.md. Merge its work into main and give me a one-line summary.
- Timestamp: 20261109T210022Z
- Run: billing api, runner actions, location cloud, id 42692774598; started 2026-11-09T21:00:22Z, ended 2026-11-09T21:01:45Z
- Account meter: no change recorded (API-billed run: the subscription's account meter does not apply)
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.42 over 12 call(s); agent $0.26, judge $0.07, guard $0.09; last agent call $0.08
- Harness: Claude Code `2.1.321 (Claude Code)`; models used: with_guidance_section=claude-sonnet-5-5; without_guidance=claude-sonnet-5-5; with_guidance_full=claude-sonnet-5-5; with_guidance_full_minus_section=claude-sonnet-5-5

| Arm | Mode | Bytes | Guard | Objective | Judge overall | Cost (USD) | Error |
| --- | --- | --- | --- | --- | --- | --- | --- |
| with_guidance_section | section | 3360 | ok (saw it); receipt ok | 1/2 | 9.0 | 0.0535 |  |
| without_guidance | none | 34 | ok (saw it); receipt ok | 1/2 | 9.3 | 0.0516 |  |
| with_guidance_full | full | 26582 | ok (saw it); receipt ok | 1/2 | 9.3 | 0.0778 |  |
| with_guidance_full_minus_section | full-minus-section | 23938 | ok (saw it); receipt ok | 1/2 | 9.7 | 0.0782 |  |
