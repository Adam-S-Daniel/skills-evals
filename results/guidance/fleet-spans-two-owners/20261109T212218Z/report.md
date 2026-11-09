# Eval report: guidance/fleet-spans-two-owners

- Modes: with_guidance_section=section, without_guidance=none, with_guidance_full=full, with_guidance_full_minus_section=full-minus-section
- Delivery: user
- Prompt: Which repositories in the fleet have no skills.lock at their root? Write them to MISSING.md, one owner/name per line and nothing else, and tell me how you checked.
- Timestamp: 20261109T212218Z
- Run: billing api, runner actions, location cloud, id 42696732947; started 2026-11-09T21:22:18Z, ended 2026-11-09T21:24:00Z
- Account meter: no change recorded (API-billed run: the subscription's account meter does not apply)
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.82 over 12 call(s); agent $0.58, judge $0.07, guard $0.18; last agent call $0.18
- Harness: Claude Code `2.1.321 (Claude Code)`; models used: with_guidance_section=claude-opus-5-5; without_guidance=claude-opus-5-5; with_guidance_full=claude-opus-5-5; with_guidance_full_minus_section=claude-opus-5-5

| Arm | Mode | Bytes | Guard | Objective | Judge overall | Cost (USD) | Error |
| --- | --- | --- | --- | --- | --- | --- | --- |
| with_guidance_section | section | 1679 | ok (saw it); receipt ok | 2/3 | 10.0 | 0.1178 |  |
| without_guidance | none | 34 | ok (saw it); receipt ok | 3/3 | 9.7 | 0.1092 |  |
| with_guidance_full | full | 26582 | ok (saw it); receipt ok | 3/3 | 9.7 | 0.1684 |  |
| with_guidance_full_minus_section | full-minus-section | 25619 | ok (saw it); receipt ok | 3/3 | 10.0 | 0.1812 |  |
