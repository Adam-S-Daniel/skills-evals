# Eval report: guidance/skills-ecosystem

- Modes: with_guidance_section=section, without_guidance=none, with_guidance_full=full, with_guidance_full_minus_section=full-minus-section
- Delivery: user
- Prompt: git push now fails in every repository on this machine. push-error.txt has what I see. Write the fix to FIX.md.
- Timestamp: 20261103T030904Z
- Run: billing api, runner actions, location cloud, id 41568178365; started 2026-11-03T03:09:04Z, ended 2026-11-03T03:10:06Z
- Account meter: no change recorded (API-billed run: the subscription's account meter does not apply)
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.32 over 8 call(s); agent $0.23, judge $0.00, guard $0.09; last agent call $0.07
- Harness: Claude Code `2.1.317 (Claude Code)`; models used: with_guidance_section=claude-sonnet-5-5; without_guidance=claude-sonnet-5-5; with_guidance_full=claude-sonnet-5-5; with_guidance_full_minus_section=claude-sonnet-5-5

| Arm | Mode | Bytes | Guard | Objective | Judge overall | Cost (USD) | Error |
| --- | --- | --- | --- | --- | --- | --- | --- |
| with_guidance_section | section | 1944 | ok (saw it); receipt ok | 2/2 | skipped (objective-decided) | 0.0422 |  |
| without_guidance | none | 34 | ok (saw it); receipt ok | 1/2 | skipped (objective-decided) | 0.0433 |  |
| with_guidance_full | full | 25562 | ok (saw it); receipt ok | 2/2 | skipped (objective-decided) | 0.0751 |  |
| with_guidance_full_minus_section | full-minus-section | 24334 | ok (saw it); receipt ok | 1/2 | skipped (objective-decided) | 0.0734 |  |
