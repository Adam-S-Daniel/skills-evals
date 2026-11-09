# Eval report: guidance/turn-lessons-into-checks

- Modes: with_guidance_section=section, without_guidance=none, with_guidance_full=full, with_guidance_full_minus_section=full-minus-section
- Delivery: user
- Prompt: The tests fail on data/rates.csv after this week's export. Fix the file, not the parser (its strictness is on purpose), and commit.
- Timestamp: 20261109T212743Z
- Run: billing api, runner actions, location cloud, id 42696732947; started 2026-11-09T21:27:43Z, ended 2026-11-09T21:30:18Z
- Account meter: no change recorded (API-billed run: the subscription's account meter does not apply)
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.99 over 8 call(s); agent $0.82, judge $0.00, guard $0.18; last agent call $0.24
- Harness: Claude Code `2.1.321 (Claude Code)`; models used: with_guidance_section=claude-opus-5-5; without_guidance=claude-opus-5-5; with_guidance_full=claude-opus-5-5; with_guidance_full_minus_section=claude-opus-5-5

| Arm | Mode | Bytes | Guard | Objective | Judge overall | Cost (USD) | Error |
| --- | --- | --- | --- | --- | --- | --- | --- |
| with_guidance_section | section | 1421 | ok (saw it); receipt ok | 4/4 | skipped (objective-decided) | 0.1809 |  |
| without_guidance | none | 34 | ok (saw it); receipt ok | 2/4 | skipped (objective-decided) | 0.1378 |  |
| with_guidance_full | full | 26582 | ok (saw it); receipt ok | 4/4 | skipped (objective-decided) | 0.2611 |  |
| with_guidance_full_minus_section | full-minus-section | 25877 | ok (saw it); receipt ok | 2/4 | skipped (objective-decided) | 0.2363 |  |
