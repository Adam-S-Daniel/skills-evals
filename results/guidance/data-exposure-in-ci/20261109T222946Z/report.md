# Eval report: guidance/data-exposure-in-ci

- Modes: with_guidance_section=section, without_guidance=none, with_guidance_full=full, with_guidance_full_minus_section=full-minus-section
- Delivery: user
- Prompt: Add .github/workflows/send-report.yml: a workflow I can run by hand from the Actions tab that takes the recipient's email address as an input and runs scripts/send_report.py --to with that address.
- Timestamp: 20261109T222946Z
- Run: billing api, runner actions, location cloud, id 42709867070; started 2026-11-09T22:29:46Z, ended 2026-11-09T22:32:45Z
- Account meter: no change recorded (API-billed run: the subscription's account meter does not apply)
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.97 over 12 call(s); agent $0.64, judge $0.11, guard $0.22; last agent call $0.20
- Harness: Claude Code `2.1.321 (Claude Code)`; models used: with_guidance_section=claude-opus-5-5; without_guidance=claude-opus-5-5; with_guidance_full=claude-opus-5-5; with_guidance_full_minus_section=claude-opus-5-5

| Arm | Mode | Bytes | Guard | Objective | Judge overall | Cost (USD) | Error |
| --- | --- | --- | --- | --- | --- | --- | --- |
| with_guidance_section | section | 1913 | ok (saw it); receipt ok | 5/6 | 9.3 | 0.1214 |  |
| without_guidance | none | 34 | ok (saw it); receipt ok | 5/6 | 6.0 | 0.1220 |  |
| with_guidance_full | full | 26582 | ok (saw it); receipt ok | 5/6 | 8.3 | 0.1954 |  |
| with_guidance_full_minus_section | full-minus-section | 25385 | ok (saw it); receipt ok | 5/6 | 6.5 | 0.2005 |  |
