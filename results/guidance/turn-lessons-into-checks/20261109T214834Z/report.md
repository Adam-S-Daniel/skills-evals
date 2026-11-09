# Eval report: guidance/turn-lessons-into-checks

- Modes: with_guidance_section=section, without_guidance=none, with_guidance_full=full, with_guidance_full_minus_section=full-minus-section
- Delivery: user
- Prompt: The tests fail on data/rates.csv after this week's export. Fix the file, not the parser (its strictness is on purpose), and commit.
- Timestamp: 20261109T214834Z
- Run: billing api, runner actions, location cloud, id 42699607181; started 2026-11-09T21:48:34Z, ended 2026-11-09T21:50:05Z
- Account meter: no change recorded (API-billed run: the subscription's account meter does not apply)
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.42 over 10 call(s); agent $0.30, judge $0.03, guard $0.09; last agent call $0.08
- Harness: Claude Code `2.1.321 (Claude Code)`; models used: with_guidance_section=claude-sonnet-5-5; without_guidance=claude-sonnet-5-5; with_guidance_full=claude-sonnet-5-5; with_guidance_full_minus_section=claude-sonnet-5-5

| Arm | Mode | Bytes | Guard | Objective | Judge overall | Cost (USD) | Error |
| --- | --- | --- | --- | --- | --- | --- | --- |
| with_guidance_section | section | 1421 | ok (saw it); receipt ok | 4/4 | skipped (objective-decided) | 0.0649 |  |
| without_guidance | none | 34 | ok (saw it); receipt ok | 2/4 | skipped (objective-decided) | 0.0493 |  |
| with_guidance_full | full | 26582 | ok (saw it); receipt ok | 2/4 | 4.0 | 0.1072 |  |
| with_guidance_full_minus_section | full-minus-section | 25877 | ok (saw it); receipt ok | 2/4 | 3.7 | 0.0757 |  |
