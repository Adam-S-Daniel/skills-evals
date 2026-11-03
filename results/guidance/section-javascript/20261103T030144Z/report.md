# Eval report: guidance/section-javascript

- Modes: with_guidance_section=section, without_guidance=none, with_guidance_full=full, with_guidance_full_minus_section=full-minus-section
- Delivery: user
- Prompt: Add fetchWithRetry(url, attempts) to src/client.js and export it: it retries a fetch that throws or returns a 5xx up to attempts times, then gives up.
- Timestamp: 20261103T030144Z
- Run: billing api, runner actions, location cloud, id 41568178365; started 2026-11-03T03:01:44Z, ended 2026-11-03T03:03:13Z
- Account meter: no change recorded (API-billed run: the subscription's account meter does not apply)
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.50 over 12 call(s); agent $0.26, judge $0.16, guard $0.09; last agent call $0.09
- Harness: Claude Code `2.1.317 (Claude Code)`; models used: with_guidance_section=claude-sonnet-5-5; without_guidance=claude-sonnet-5-5; with_guidance_full=claude-sonnet-5-5; with_guidance_full_minus_section=claude-sonnet-5-5

| Arm | Mode | Bytes | Guard | Objective | Judge overall | Cost (USD) | Error |
| --- | --- | --- | --- | --- | --- | --- | --- |
| with_guidance_section | section | 283 | ok (saw it); receipt ok | 3/3 | 10.0 | 0.0506 |  |
| without_guidance | none | 34 | ok (saw it); receipt ok | 3/3 | 10.0 | 0.0364 |  |
| with_guidance_full | full | 25811 | ok (saw it); receipt ok | 3/3 | 10.0 | 0.0830 |  |
| with_guidance_full_minus_section | full-minus-section | 25562 | ok (saw it); receipt ok | 3/3 | 10.0 | 0.0869 |  |
