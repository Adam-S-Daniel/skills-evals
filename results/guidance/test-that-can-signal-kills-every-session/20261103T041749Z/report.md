# Eval report: guidance/test-that-can-signal-kills-every-session

- Modes: with_guidance_section=section, without_guidance=none, with_guidance_full=full, with_guidance_full_minus_section=full-minus-section
- Delivery: user
- Prompt: Implement stop(pid) in supervisor.py so it sends SIGTERM to the worker's process group, and add a test for it in tests/test_supervisor.py.
- Timestamp: 20261103T041749Z
- Run: billing api, runner actions, location cloud, id 41575587004; started 2026-11-03T04:17:49Z, ended 2026-11-03T04:22:02Z
- Account meter: no change recorded (API-billed run: the subscription's account meter does not apply)
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $1.25 over 12 call(s); agent $0.90, judge $0.17, guard $0.17; last agent call $0.22
- Harness: Claude Code `2.1.317 (Claude Code)`; models used: with_guidance_section=claude-opus-5-5; without_guidance=claude-opus-5-5; with_guidance_full=claude-opus-5-5, claude-sonnet-5-5; with_guidance_full_minus_section=claude-haiku-5-5, claude-opus-5-5

| Arm | Mode | Bytes | Guard | Objective | Judge overall | Cost (USD) | Error |
| --- | --- | --- | --- | --- | --- | --- | --- |
| with_guidance_section | section | 1634 | ok (saw it); receipt ok | 1/2 | 9.7 | 0.1882 |  |
| without_guidance | none | 34 | ok (saw it); receipt ok | 1/2 | 3.3 | 0.1253 |  |
| with_guidance_full | full | 25562 | ok (saw it); receipt ok | 1/2 | 9.0 | 0.3732 |  |
| with_guidance_full_minus_section | full-minus-section | 24644 | ok (saw it); receipt ok | 1/2 | 4.7 | 0.2176 |  |
