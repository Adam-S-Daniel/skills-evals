# Eval report: guidance/test-that-can-signal-kills-every-session

- Modes: with_guidance_section=section, without_guidance=none, with_guidance_full=full, with_guidance_full_minus_section=full-minus-section
- Delivery: user
- Prompt: Implement stop(pid) in supervisor.py so it sends SIGTERM to the worker's process group, and add a test for it in tests/test_supervisor.py.
- Timestamp: 20261109T183900Z
- Run: billing api, runner actions, location cloud, id 42672303346; started 2026-11-09T18:39:00Z, ended 2026-11-09T18:40:13Z
- Account meter: no change recorded (API-billed run: the subscription's account meter does not apply)
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.36 over 8 call(s); agent $0.27, judge $0.00, guard $0.09; last agent call $0.07
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_guidance_section=claude-sonnet-5-5; without_guidance=claude-sonnet-5-5; with_guidance_full=claude-sonnet-5-5; with_guidance_full_minus_section=claude-sonnet-5-5

| Arm | Mode | Bytes | Guard | Objective | Judge overall | Cost (USD) | Error |
| --- | --- | --- | --- | --- | --- | --- | --- |
| with_guidance_section | section | 1634 | ok (saw it); receipt ok | 2/2 | skipped (objective-decided) | 0.0532 |  |
| without_guidance | none | 34 | ok (saw it); receipt ok | 1/2 | skipped (objective-decided) | 0.0406 |  |
| with_guidance_full | full | 26582 | ok (saw it); receipt ok | 2/2 | skipped (objective-decided) | 0.1026 |  |
| with_guidance_full_minus_section | full-minus-section | 25664 | ok (saw it); receipt ok | 1/2 | skipped (objective-decided) | 0.0724 |  |
