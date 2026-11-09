# Eval report: guidance/automation-vs-branch-protection

- Modes: with_guidance_section=section, without_guidance=none, with_guidance_full=full, with_guidance_full_minus_section=full-minus-section
- Delivery: user
- Prompt: Every time someone adds a label to a pull request, ci.yml runs the whole test job again and we pay for the duplicate. Stop the duplicate runs, and keep the e2e label working.
- Timestamp: 20261109T213726Z
- Run: billing api, runner actions, location cloud, id 42699607181; started 2026-11-09T21:37:26Z, ended 2026-11-09T21:38:43Z
- Account meter: no change recorded (API-billed run: the subscription's account meter does not apply)
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.39 over 10 call(s); agent $0.23, judge $0.05, guard $0.11; last agent call $0.07
- Harness: Claude Code `2.1.321 (Claude Code)`; models used: with_guidance_section=claude-sonnet-5-5; without_guidance=claude-sonnet-5-5; with_guidance_full=claude-sonnet-5-5; with_guidance_full_minus_section=claude-sonnet-5-5

| Arm | Mode | Bytes | Guard | Objective | Judge overall | Cost (USD) | Error |
| --- | --- | --- | --- | --- | --- | --- | --- |
| with_guidance_section | section | 2917 | ok (saw it); receipt ok | 3/4 | 8.0 | 0.0441 |  |
| without_guidance | none | 34 | ok (saw it); receipt ok | 3/4 | 6.5 | 0.0388 |  |
| with_guidance_full | full | 26582 | ok (saw it); receipt ok | 4/4 | skipped (objective-decided) | 0.0810 |  |
| with_guidance_full_minus_section | full-minus-section | 24381 | ok (saw it); receipt ok | 3/4 | skipped (objective-decided) | 0.0657 |  |
