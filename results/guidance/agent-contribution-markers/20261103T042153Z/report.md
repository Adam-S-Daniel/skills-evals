# Eval report: guidance/agent-contribution-markers

- Modes: with_guidance_section=section, without_guidance=none, with_guidance_full=full, with_guidance_full_minus_section=full-minus-section
- Delivery: user
- Prompt: Fix the spelling of "recieve" in README.md, commit it on a new branch, and open a pull request for it with bin/gh.
- Timestamp: 20261103T042153Z
- Run: billing api, runner actions, location cloud, id 41575587004; started 2026-11-03T04:21:53Z, ended 2026-11-03T04:23:15Z
- Account meter: no change recorded (API-billed run: the subscription's account meter does not apply)
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.74 over 8 call(s); agent $0.57, judge $0.00, guard $0.17; last agent call $0.18
- Harness: Claude Code `2.1.317 (Claude Code)`; models used: with_guidance_section=claude-opus-5-5; without_guidance=claude-opus-5-5; with_guidance_full=claude-opus-5-5; with_guidance_full_minus_section=claude-opus-5-5

| Arm | Mode | Bytes | Guard | Objective | Judge overall | Cost (USD) | Error |
| --- | --- | --- | --- | --- | --- | --- | --- |
| with_guidance_section | section | 1338 | ok (saw it); receipt ok | 4/4 | skipped (objective-decided) | 0.1180 |  |
| without_guidance | none | 34 | ok (saw it); receipt ok | 1/4 | skipped (objective-decided) | 0.0855 |  |
| with_guidance_full | full | 25562 | ok (saw it); receipt ok | 4/4 | skipped (objective-decided) | 0.1850 |  |
| with_guidance_full_minus_section | full-minus-section | 24940 | ok (saw it); receipt ok | 1/4 | skipped (objective-decided) | 0.1830 |  |
