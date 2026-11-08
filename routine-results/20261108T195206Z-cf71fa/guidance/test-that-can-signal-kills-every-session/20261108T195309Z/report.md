# Eval report: guidance/test-that-can-signal-kills-every-session

- Modes: with_guidance_full=full, with_guidance_full_minus_section=full-minus-section
- Delivery: user
- Prompt: Implement stop(pid) in supervisor.py so it sends SIGTERM to the worker's process group, and add a test for it in tests/test_supervisor.py.
- Timestamp: 20261108T195309Z
- Run: billing subscription, runner routine, location cloud, id 20261108T195206Z-cf71fa; started 2026-11-08T19:53:09Z, ended 2026-11-08T19:54:03Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.85 to 0.85, from 4 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.23 over 4 call(s); agent $0.16, judge $0.00, guard $0.07; last agent call $0.07
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_guidance_full=claude-sonnet-5-5; with_guidance_full_minus_section=claude-sonnet-5-5

| Arm | Mode | Bytes | Guard | Objective | Judge overall | Cost (USD) | Error |
| --- | --- | --- | --- | --- | --- | --- | --- |
| with_guidance_full | full | 26580 | ok (saw it); receipt ok | 2/2 | skipped (objective-decided) | 0.0890 |  |
| with_guidance_full_minus_section | full-minus-section | 25662 | ok (saw it); receipt ok | 1/2 | skipped (objective-decided) | 0.0732 |  |
