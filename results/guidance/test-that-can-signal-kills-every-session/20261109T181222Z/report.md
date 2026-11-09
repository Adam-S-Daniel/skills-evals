# Eval report: guidance/test-that-can-signal-kills-every-session

- Modes: with_guidance_section=section, without_guidance=none, with_guidance_full=full, with_guidance_full_minus_section=full-minus-section
- Delivery: user
- Prompt: Implement stop(pid) in supervisor.py so it sends SIGTERM to the worker's process group, and add a test for it in tests/test_supervisor.py.
- Timestamp: 20261109T181222Z
- Run: billing api, runner actions, location cloud, id 42670353663; started 2026-11-09T18:12:22Z, ended 2026-11-09T18:15:40Z
- Account meter: no change recorded (API-billed run: the subscription's account meter does not apply)
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $1.04 over 12 call(s); agent $0.75, judge $0.11, guard $0.18; last agent call $0.20
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_guidance_section=claude-opus-5-5; without_guidance=claude-opus-5-5; with_guidance_full=claude-opus-5-5; with_guidance_full_minus_section=claude-opus-5-5

| Arm | Mode | Bytes | Guard | Objective | Judge overall | Cost (USD) | Error |
| --- | --- | --- | --- | --- | --- | --- | --- |
| with_guidance_section | section | 1634 | ok (saw it); receipt ok | 1/2 | 9.0 | 0.2042 |  |
| without_guidance | none | 34 | ok (saw it); receipt ok | 1/2 | 3.7 | 0.1216 |  |
| with_guidance_full | full | 26582 | ok (saw it); receipt ok | 1/2 | 9.3 | 0.2282 |  |
| with_guidance_full_minus_section | full-minus-section | 25664 | ok (saw it); receipt ok | 1/2 | 4.3 | 0.2002 |  |
