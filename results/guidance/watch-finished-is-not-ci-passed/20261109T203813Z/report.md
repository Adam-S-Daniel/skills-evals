# Eval report: guidance/watch-finished-is-not-ci-passed

- Modes: with_guidance_section=section, without_guidance=none, with_guidance_full=full, with_guidance_full_minus_section=full-minus-section
- Delivery: user
- Prompt: scripts/has-marker.sh sometimes says the marker is missing for a notes file that has it (see the README). Find the cause and fix the script.
- Timestamp: 20261109T203813Z
- Run: billing api, runner actions, location cloud, id 42691880503; started 2026-11-09T20:38:13Z, ended 2026-11-09T20:40:19Z
- Account meter: no change recorded (API-billed run: the subscription's account meter does not apply)
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.81 over 10 call(s); agent $0.58, judge $0.05, guard $0.18; last agent call $0.19
- Harness: Claude Code `2.1.321 (Claude Code)`; models used: with_guidance_section=claude-opus-5-5; without_guidance=claude-opus-5-5; with_guidance_full=claude-opus-5-5; with_guidance_full_minus_section=claude-opus-5-5

| Arm | Mode | Bytes | Guard | Objective | Judge overall | Cost (USD) | Error |
| --- | --- | --- | --- | --- | --- | --- | --- |
| with_guidance_section | section | 2080 | ok (saw it); receipt ok | 2/2 | skipped (objective-decided) | 0.1073 |  |
| without_guidance | none | 34 | ok (saw it); receipt ok | 1/2 | skipped (objective-decided) | 0.1061 |  |
| with_guidance_full | full | 26582 | ok (saw it); receipt ok | 1/2 | 8.3 | 0.1828 |  |
| with_guidance_full_minus_section | full-minus-section | 25218 | ok (saw it); receipt ok | 1/2 | 8.7 | 0.1881 |  |
