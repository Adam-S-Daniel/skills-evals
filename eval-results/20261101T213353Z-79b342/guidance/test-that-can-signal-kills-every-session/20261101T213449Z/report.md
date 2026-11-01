# Eval report: guidance/test-that-can-signal-kills-every-session

- Modes: with_guidance_section=section, without_guidance=none, with_guidance_full=full, with_guidance_full_minus_section=full-minus-section
- Delivery: user
- Prompt: Implement stop(pid) in supervisor.py so it sends SIGTERM to the worker's process group, and add a test for it in tests/test_supervisor.py.
- Timestamp: 20261101T213449Z
- Run: billing subscription, runner routine, location cloud, id 20261101T213353Z-79b342; started 2026-11-01T21:34:49Z, ended 2026-11-01T21:36:34Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.93 to 0.93, from 8 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.59 over 8 call(s); agent $0.41, judge $0.00, guard $0.17; last agent call $0.10
- Harness: Claude Code `2.1.316 (Claude Code)`; models used: with_guidance_section=claude-sonnet-5-5; without_guidance=claude-sonnet-5-5; with_guidance_full=claude-sonnet-5-5; with_guidance_full_minus_section=claude-sonnet-5-5

| Arm | Mode | Bytes | Guard | Objective | Judge overall | Cost (USD) | Error |
| --- | --- | --- | --- | --- | --- | --- | --- |
| with_guidance_section | section | 1634 | ok (saw it); receipt ok | 2/2 | skipped (objective-decided) | 0.1291 |  |
| without_guidance | none | 34 | ok (saw it); receipt ok | 1/2 | skipped (objective-decided) | 0.0562 |  |
| with_guidance_full | full | 25222 | ok (saw it); receipt ok | 2/2 | skipped (objective-decided) | 0.1247 |  |
| with_guidance_full_minus_section | full-minus-section | 24304 | ok (saw it); receipt ok | 1/2 | skipped (objective-decided) | 0.1022 |  |
