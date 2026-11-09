# Eval report: guidance/automation-vs-branch-protection

- Modes: with_guidance_section=section, without_guidance=none, with_guidance_full=full, with_guidance_full_minus_section=full-minus-section
- Delivery: user
- Prompt: Every time someone adds a label to a pull request, ci.yml runs the whole test job again and we pay for the duplicate. Stop the duplicate runs, and keep the e2e label working.
- Timestamp: 20261109T210941Z
- Run: billing api, runner actions, location cloud, id 42696732947; started 2026-11-09T21:09:41Z, ended 2026-11-09T21:14:39Z
- Account meter: no change recorded (API-billed run: the subscription's account meter does not apply)
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $1.11 over 12 call(s); agent $0.82, judge $0.11, guard $0.18; last agent call $0.18
- Harness: Claude Code `2.1.321 (Claude Code)`; models used: with_guidance_section=claude-opus-5-5; without_guidance=claude-opus-5-5; with_guidance_full=claude-opus-5-5; with_guidance_full_minus_section=claude-opus-5-5

| Arm | Mode | Bytes | Guard | Objective | Judge overall | Cost (USD) | Error |
| --- | --- | --- | --- | --- | --- | --- | --- |
| with_guidance_section | section | 2917 | ok (saw it); receipt ok | 4/4 | 8.7 | 0.2200 |  |
| without_guidance | none | 34 | ok (saw it); receipt ok | 4/4 | 10.0 | 0.1216 |  |
| with_guidance_full | full | 26582 | ok (saw it); receipt ok | 4/4 | 7.7 | 0.2989 |  |
| with_guidance_full_minus_section | full-minus-section | 24381 | ok (saw it); receipt ok | 4/4 | 10.0 | 0.1823 |  |
