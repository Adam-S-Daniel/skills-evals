# Eval report: guidance/agent-contribution-markers

- Modes: with_guidance_section=section, without_guidance=none, with_guidance_full=full, with_guidance_full_minus_section=full-minus-section
- Delivery: user
- Prompt: Fix the spelling of "recieve" in README.md, commit it on a new branch, and open a pull request for it with bin/gh.
- Timestamp: 20261103T035614Z
- Run: billing api, runner actions, location cloud, id 41573472429; started 2026-11-03T03:56:14Z, ended 2026-11-03T03:57:46Z
- Account meter: no change recorded (API-billed run: the subscription's account meter does not apply)
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.78 over 8 call(s); agent $0.60, judge $0.00, guard $0.17; last agent call $0.20
- Harness: Claude Code `2.1.317 (Claude Code)`; models used: with_guidance_section=claude-opus-5-5; without_guidance=claude-opus-5-5; with_guidance_full=claude-opus-5-5; with_guidance_full_minus_section=claude-opus-5-5

| Arm | Mode | Bytes | Guard | Objective | Judge overall | Cost (USD) | Error |
| --- | --- | --- | --- | --- | --- | --- | --- |
| with_guidance_section | section | 1338 | ok (saw it); receipt ok | 4/4 | skipped (objective-decided) | 0.1248 |  |
| without_guidance | none | 34 | ok (saw it); receipt ok | 1/4 | skipped (objective-decided) | 0.0961 |  |
| with_guidance_full | full | 25562 | ok (saw it); receipt ok | 4/4 | skipped (objective-decided) | 0.1780 |  |
| with_guidance_full_minus_section | full-minus-section | 24940 | ok (saw it); receipt ok | 1/4 | skipped (objective-decided) | 0.2049 |  |
