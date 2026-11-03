# Eval report: guidance/automation-vs-branch-protection

- Modes: with_guidance_section=section, without_guidance=none, with_guidance_full=full, with_guidance_full_minus_section=full-minus-section
- Delivery: user
- Prompt: Every time someone adds a label to a pull request, ci.yml runs the whole test job again and we pay for the duplicate. Stop the duplicate runs, and keep the e2e label working.
- Timestamp: 20261103T022748Z
- Run: billing api, runner actions, location cloud, id 41565470204; started 2026-11-03T02:27:48Z, ended 2026-11-03T02:29:23Z
- Account meter: no change recorded (API-billed run: the subscription's account meter does not apply)
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.49 over 12 call(s); agent $0.22, judge $0.18, guard $0.09; last agent call $0.07
- Harness: Claude Code `2.1.317 (Claude Code)`; models used: with_guidance_section=claude-sonnet-5-5; without_guidance=claude-sonnet-5-5; with_guidance_full=claude-sonnet-5-5; with_guidance_full_minus_section=claude-sonnet-5-5

| Arm | Mode | Bytes | Guard | Objective | Judge overall | Cost (USD) | Error |
| --- | --- | --- | --- | --- | --- | --- | --- |
| with_guidance_section | section | 2917 | ok (saw it); receipt ok | 3/4 | 7.0 | 0.0436 |  |
| without_guidance | none | 34 | ok (saw it); receipt ok | 3/4 | 6.0 | 0.0369 |  |
| with_guidance_full | full | 25562 | ok (saw it); receipt ok | 3/4 | 7.0 | 0.0762 |  |
| with_guidance_full_minus_section | full-minus-section | 23361 | ok (saw it); receipt ok | 3/4 | 6.5 | 0.0653 |  |
