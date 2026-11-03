# Eval report: guidance/section-typescript

- Modes: with_guidance_section=section, without_guidance=none, with_guidance_full=full, with_guidance_full_minus_section=full-minus-section
- Delivery: user
- Prompt: Add parseEvent(raw: string): Event to src/events.ts. It parses a JSON webhook payload and throws if the payload is not a valid Event.
- Timestamp: 20261103T052428Z
- Run: billing api, runner actions, location cloud, id 41582448832; started 2026-11-03T05:24:28Z, ended 2026-11-03T05:27:25Z
- Account meter: no change recorded (API-billed run: the subscription's account meter does not apply)
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $1.09 over 12 call(s); agent $0.76, judge $0.16, guard $0.17; last agent call $0.32
- Harness: Claude Code `2.1.317 (Claude Code)`; models used: with_guidance_section=claude-opus-5-5; without_guidance=claude-opus-5-5; with_guidance_full=claude-haiku-5-5, claude-opus-5-5; with_guidance_full_minus_section=claude-opus-5-5, claude-sonnet-5-5

| Arm | Mode | Bytes | Guard | Objective | Judge overall | Cost (USD) | Error |
| --- | --- | --- | --- | --- | --- | --- | --- |
| with_guidance_section | section | 560 | ok (saw it); receipt ok | 3/3 | 9.7 | 0.1097 |  |
| without_guidance | none | 34 | ok (saw it); receipt ok | 3/3 | 9.3 | 0.1175 |  |
| with_guidance_full | full | 26088 | ok (saw it); receipt ok | 3/3 | 9.3 | 0.2097 |  |
| with_guidance_full_minus_section | full-minus-section | 25562 | ok (saw it); receipt ok | 3/3 | 9.3 | 0.3184 |  |
