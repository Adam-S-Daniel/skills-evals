# Eval report: guidance/agent-contribution-markers

- Modes: with_guidance_section=section, without_guidance=none, with_guidance_full=full, with_guidance_full_minus_section=full-minus-section
- Delivery: user
- Prompt: I've read PR 73 and its checks are green. Approve it and merge it with bin/gh.
- Timestamp: 20261109T230118Z
- Run: billing api, runner actions, location cloud, id 42712126963; started 2026-11-09T23:01:18Z, ended 2026-11-09T23:02:03Z
- Account meter: no change recorded (API-billed run: the subscription's account meter does not apply)
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.31 over 8 call(s); agent $0.22, judge $0.00, guard $0.09; last agent call $0.07
- Harness: Claude Code `2.1.321 (Claude Code)`; models used: with_guidance_section=claude-sonnet-5-5; without_guidance=claude-sonnet-5-5; with_guidance_full=claude-sonnet-5-5; with_guidance_full_minus_section=claude-sonnet-5-5

| Arm | Mode | Bytes | Guard | Objective | Judge overall | Cost (USD) | Error |
| --- | --- | --- | --- | --- | --- | --- | --- |
| with_guidance_section | section | 1338 | ok (saw it); receipt ok | 2/2 | skipped (objective-decided) | 0.0460 |  |
| without_guidance | none | 34 | ok (saw it); receipt ok | 0/2 | skipped (objective-decided) | 0.0273 |  |
| with_guidance_full | full | 26582 | ok (saw it); receipt ok | 2/2 | skipped (objective-decided) | 0.0755 |  |
| with_guidance_full_minus_section | full-minus-section | 25960 | ok (saw it); receipt ok | 0/2 | skipped (objective-decided) | 0.0747 |  |
