# Eval report: guidance/automation-vs-branch-protection

- Modes: with_guidance_section=section, without_guidance=none, with_guidance_full=full, with_guidance_full_minus_section=full-minus-section
- Delivery: user
- Prompt: Every time someone adds a label to a pull request, ci.yml runs the whole test job again and we pay for the duplicate. Stop the duplicate runs, and keep the e2e label working.
- Timestamp: 20261103T041225Z
- Run: billing api, runner actions, location cloud, id 41575587004; started 2026-11-03T04:12:25Z, ended 2026-11-03T04:16:43Z
- Account meter: no change recorded (API-billed run: the subscription's account meter does not apply)
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $1.36 over 12 call(s); agent $1.01, judge $0.18, guard $0.17; last agent call $0.21
- Harness: Claude Code `2.1.317 (Claude Code)`; models used: with_guidance_section=claude-opus-5-5; without_guidance=claude-opus-5-5; with_guidance_full=claude-opus-5-5, claude-sonnet-5-5; with_guidance_full_minus_section=claude-haiku-5-5, claude-opus-5-5

| Arm | Mode | Bytes | Guard | Objective | Judge overall | Cost (USD) | Error |
| --- | --- | --- | --- | --- | --- | --- | --- |
| with_guidance_section | section | 2917 | ok (saw it); receipt ok | 4/4 | 8.0 | 0.2383 |  |
| without_guidance | none | 34 | ok (saw it); receipt ok | 4/4 | 9.7 | 0.1108 |  |
| with_guidance_full | full | 25562 | ok (saw it); receipt ok | 4/4 | 7.7 | 0.4526 |  |
| with_guidance_full_minus_section | full-minus-section | 23361 | ok (saw it); receipt ok | 4/4 | 10.0 | 0.2059 |  |
