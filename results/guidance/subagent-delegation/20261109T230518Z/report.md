# Eval report: guidance/subagent-delegation

- Modes: with_guidance_section=section, without_guidance=none, with_guidance_full=full, with_guidance_full_minus_section=full-minus-section
- Delivery: user
- Prompt: I want to hand TASK.md to a subagent and not look at it again until it reports. Do not do the rename yourself. Write the complete prompt you would give the subagent, plus the settings you would delegate it with, to HANDOFF.md.
- Timestamp: 20261109T230518Z
- Run: billing api, runner actions, location cloud, id 42712126963; started 2026-11-09T23:05:18Z, ended 2026-11-09T23:07:02Z
- Account meter: no change recorded (API-billed run: the subscription's account meter does not apply)
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.41 over 8 call(s); agent $0.33, judge $0.00, guard $0.09; last agent call $0.09
- Harness: Claude Code `2.1.321 (Claude Code)`; models used: with_guidance_section=claude-sonnet-5-5; without_guidance=claude-sonnet-5-5; with_guidance_full=claude-sonnet-5-5; with_guidance_full_minus_section=claude-sonnet-5-5

| Arm | Mode | Bytes | Guard | Objective | Judge overall | Cost (USD) | Error |
| --- | --- | --- | --- | --- | --- | --- | --- |
| with_guidance_section | section | 3360 | ok (saw it); receipt ok | 3/3 | skipped (objective-decided) | 0.0729 |  |
| without_guidance | none | 34 | ok (saw it); receipt ok | 2/3 | skipped (objective-decided) | 0.0675 |  |
| with_guidance_full | full | 26582 | ok (saw it); receipt ok | 3/3 | skipped (objective-decided) | 0.0969 |  |
| with_guidance_full_minus_section | full-minus-section | 23938 | ok (saw it); receipt ok | 1/3 | skipped (objective-decided) | 0.0877 |  |
