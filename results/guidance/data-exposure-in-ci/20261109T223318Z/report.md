# Eval report: guidance/data-exposure-in-ci

- Modes: with_guidance_section=section, without_guidance=none, with_guidance_full=full, with_guidance_full_minus_section=full-minus-section
- Delivery: user
- Prompt: Take the hard-coded recipient address out of .github/workflows/weekly-digest.yml so I can change who gets the digest without a commit.
- Timestamp: 20261109T223318Z
- Run: billing api, runner actions, location cloud, id 42709867070; started 2026-11-09T22:33:18Z, ended 2026-11-09T22:35:24Z
- Account meter: no change recorded (API-billed run: the subscription's account meter does not apply)
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.85 over 12 call(s); agent $0.59, judge $0.08, guard $0.18; last agent call $0.17
- Harness: Claude Code `2.1.321 (Claude Code)`; models used: with_guidance_section=claude-opus-5-5; without_guidance=claude-opus-5-5; with_guidance_full=claude-opus-5-5; with_guidance_full_minus_section=claude-opus-5-5

| Arm | Mode | Bytes | Guard | Objective | Judge overall | Cost (USD) | Error |
| --- | --- | --- | --- | --- | --- | --- | --- |
| with_guidance_section | section | 1913 | ok (saw it); receipt ok | 3/3 | 9.0 | 0.1021 |  |
| without_guidance | none | 34 | ok (saw it); receipt ok | 3/3 | 8.7 | 0.1034 |  |
| with_guidance_full | full | 26582 | ok (saw it); receipt ok | 3/3 | 8.3 | 0.2106 |  |
| with_guidance_full_minus_section | full-minus-section | 25385 | ok (saw it); receipt ok | 3/3 | 9.0 | 0.1741 |  |
