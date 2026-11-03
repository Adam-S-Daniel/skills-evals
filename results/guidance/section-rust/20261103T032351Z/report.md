# Eval report: guidance/section-rust

- Modes: with_guidance_section=section, without_guidance=none, with_guidance_full=full, with_guidance_full_minus_section=full-minus-section
- Delivery: user
- Prompt: Add two public functions to src/lib.rs: parse_port(value: &str), which turns a string into a port number (1-65535), and port_from_env(), which reads it from the PORT variable. Use ConfigError for failures. Put their tests in tests/port.rs.
- Timestamp: 20261103T032351Z
- Run: billing api, runner actions, location cloud, id 41570821022; started 2026-11-03T03:23:51Z, ended 2026-11-03T03:25:37Z
- Account meter: no change recorded (API-billed run: the subscription's account meter does not apply)
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.53 over 12 call(s); agent $0.27, judge $0.17, guard $0.09; last agent call $0.08
- Harness: Claude Code `2.1.317 (Claude Code)`; models used: with_guidance_section=claude-sonnet-5-5; without_guidance=claude-sonnet-5-5; with_guidance_full=claude-sonnet-5-5; with_guidance_full_minus_section=claude-sonnet-5-5

| Arm | Mode | Bytes | Guard | Objective | Judge overall | Cost (USD) | Error |
| --- | --- | --- | --- | --- | --- | --- | --- |
| with_guidance_section | section | 339 | ok (saw it); receipt ok | 3/3 | 9.3 | 0.0552 |  |
| without_guidance | none | 34 | ok (saw it); receipt ok | 3/3 | 9.7 | 0.0547 |  |
| with_guidance_full | full | 25867 | ok (saw it); receipt ok | 3/3 | 9.3 | 0.0821 |  |
| with_guidance_full_minus_section | full-minus-section | 25562 | ok (saw it); receipt ok | 3/3 | 10.0 | 0.0804 |  |
