# Eval report: guidance/turn-lessons-into-checks

- Modes: with_guidance_section=section, without_guidance=none, with_guidance_full=full, with_guidance_full_minus_section=full-minus-section
- Delivery: user
- Prompt: Someone left a breakpoint() in src/app.py again and it hung the worker in production. Take it out and commit.
- Timestamp: 20261109T215715Z
- Run: billing api, runner actions, location cloud, id 42704067783; started 2026-11-09T21:57:15Z, ended 2026-11-09T22:00:16Z
- Account meter: no change recorded (API-billed run: the subscription's account meter does not apply)
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $1.09 over 10 call(s); agent $0.86, judge $0.05, guard $0.18; last agent call $0.29
- Harness: Claude Code `2.1.321 (Claude Code)`; models used: with_guidance_section=claude-opus-5-5; without_guidance=claude-opus-5-5; with_guidance_full=claude-opus-5-5; with_guidance_full_minus_section=claude-opus-5-5

| Arm | Mode | Bytes | Guard | Objective | Judge overall | Cost (USD) | Error |
| --- | --- | --- | --- | --- | --- | --- | --- |
| with_guidance_section | section | 1421 | ok (saw it); receipt ok | 3/3 | skipped (objective-decided) | 0.1674 |  |
| without_guidance | none | 34 | ok (saw it); receipt ok | 1/3 | skipped (objective-decided) | 0.1327 |  |
| with_guidance_full | full | 26582 | ok (saw it); receipt ok | 2/3 | 6.7 | 0.2678 |  |
| with_guidance_full_minus_section | full-minus-section | 25877 | ok (saw it); receipt ok | 2/3 | 6.7 | 0.2936 |  |
