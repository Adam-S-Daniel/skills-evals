# Eval report: guidance/watch-finished-is-not-ci-passed

- Modes: with_guidance_section=section, without_guidance=none, with_guidance_full=full, with_guidance_full_minus_section=full-minus-section
- Delivery: user
- Prompt: scripts/has-marker.sh sometimes says the marker is missing for a notes file that has it (see the README). Find the cause and fix the script.
- Timestamp: 20261109T181523Z
- Run: billing api, runner actions, location cloud, id 42670353663; started 2026-11-09T18:15:23Z, ended 2026-11-09T18:17:27Z
- Account meter: no change recorded (API-billed run: the subscription's account meter does not apply)
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.80 over 10 call(s); agent $0.59, judge $0.04, guard $0.18; last agent call $0.18
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_guidance_section=claude-opus-5-5; without_guidance=claude-opus-5-5; with_guidance_full=claude-opus-5-5; with_guidance_full_minus_section=claude-opus-5-5

| Arm | Mode | Bytes | Guard | Objective | Judge overall | Cost (USD) | Error |
| --- | --- | --- | --- | --- | --- | --- | --- |
| with_guidance_section | section | 2080 | ok (saw it); receipt ok | 1/2 | 9.0 | 0.1149 |  |
| without_guidance | none | 34 | ok (saw it); receipt ok | 1/2 | 9.3 | 0.1051 |  |
| with_guidance_full | full | 26582 | ok (saw it); receipt ok | 2/2 | skipped (objective-decided) | 0.1896 |  |
| with_guidance_full_minus_section | full-minus-section | 25218 | ok (saw it); receipt ok | 1/2 | skipped (objective-decided) | 0.1777 |  |
