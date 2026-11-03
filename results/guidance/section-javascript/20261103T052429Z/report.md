# Eval report: guidance/section-javascript

- Modes: with_guidance_section=section, without_guidance=none, with_guidance_full=full, with_guidance_full_minus_section=full-minus-section
- Delivery: user
- Prompt: Add fetchWithRetry(url, attempts) to src/client.js and export it: it retries a fetch that throws or returns a 5xx up to attempts times, then gives up.
- Timestamp: 20261103T052429Z
- Run: billing api, runner actions, location cloud, id 41582448832; started 2026-11-03T05:24:29Z, ended 2026-11-03T05:27:22Z
- Account meter: no change recorded (API-billed run: the subscription's account meter does not apply)
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $1.13 over 12 call(s); agent $0.79, judge $0.17, guard $0.17; last agent call $0.29
- Harness: Claude Code `2.1.317 (Claude Code)`; models used: with_guidance_section=claude-opus-5-5; without_guidance=claude-opus-5-5; with_guidance_full=claude-opus-5-5, claude-sonnet-5-5; with_guidance_full_minus_section=claude-opus-5-5, claude-sonnet-5-5

| Arm | Mode | Bytes | Guard | Objective | Judge overall | Cost (USD) | Error |
| --- | --- | --- | --- | --- | --- | --- | --- |
| with_guidance_section | section | 283 | ok (saw it); receipt ok | 3/3 | 10.0 | 0.1078 |  |
| without_guidance | none | 34 | ok (saw it); receipt ok | 3/3 | 10.0 | 0.0877 |  |
| with_guidance_full | full | 25811 | ok (saw it); receipt ok | 3/3 | 10.0 | 0.3063 |  |
| with_guidance_full_minus_section | full-minus-section | 25562 | ok (saw it); receipt ok | 3/3 | 10.0 | 0.2920 |  |
