# Eval report: guidance/workstation-layout

- Modes: with_guidance_section=section, without_guidance=none, with_guidance_full=full, with_guidance_full_minus_section=full-minus-section
- Delivery: user
- Prompt: Write clone-all.ps1: it clones every repository in repos.txt from GitHub into the place clones live on my Windows workstation, skipping any that are already there.
- Timestamp: 20261103T032626Z
- Run: billing api, runner actions, location cloud, id 41570821022; started 2026-11-03T03:26:26Z, ended 2026-11-03T03:27:45Z
- Account meter: no change recorded (API-billed run: the subscription's account meter does not apply)
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.37 over 8 call(s); agent $0.28, judge $0.00, guard $0.09; last agent call $0.10
- Harness: Claude Code `2.1.317 (Claude Code)`; models used: with_guidance_section=claude-sonnet-5-5; without_guidance=claude-sonnet-5-5; with_guidance_full=claude-sonnet-5-5; with_guidance_full_minus_section=claude-sonnet-5-5

| Arm | Mode | Bytes | Guard | Objective | Judge overall | Cost (USD) | Error |
| --- | --- | --- | --- | --- | --- | --- | --- |
| with_guidance_section | section | 865 | ok (saw it); receipt ok | 2/2 | skipped (objective-decided) | 0.0470 |  |
| without_guidance | none | 34 | ok (saw it); receipt ok | 0/2 | skipped (objective-decided) | 0.0539 |  |
| with_guidance_full | full | 25562 | ok (saw it); receipt ok | 2/2 | skipped (objective-decided) | 0.0798 |  |
| with_guidance_full_minus_section | full-minus-section | 25413 | ok (saw it); receipt ok | 0/2 | skipped (objective-decided) | 0.0992 |  |
