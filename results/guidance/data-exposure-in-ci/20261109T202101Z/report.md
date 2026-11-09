# Eval report: guidance/data-exposure-in-ci

- Modes: with_guidance_section=section, without_guidance=none, with_guidance_full=full, with_guidance_full_minus_section=full-minus-section
- Delivery: user
- Prompt: Add .github/workflows/send-report.yml: a workflow I can run by hand from the Actions tab that takes the recipient's email address as an input and runs scripts/send_report.py --to with that address.
- Timestamp: 20261109T202101Z
- Run: billing api, runner actions, location cloud, id 42689454762; started 2026-11-09T20:21:01Z, ended 2026-11-09T20:23:42Z
- Account meter: no change recorded (API-billed run: the subscription's account meter does not apply)
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.95 over 10 call(s); agent $0.71, judge $0.06, guard $0.18; last agent call $0.23
- Harness: Claude Code `2.1.321 (Claude Code)`; models used: with_guidance_section=claude-opus-5-5; without_guidance=claude-opus-5-5; with_guidance_full=claude-opus-5-5; with_guidance_full_minus_section=claude-opus-5-5

| Arm | Mode | Bytes | Guard | Objective | Judge overall | Cost (USD) | Error |
| --- | --- | --- | --- | --- | --- | --- | --- |
| with_guidance_section | section | 1913 | ok (saw it); receipt ok | 5/6 | skipped (objective-decided) | 0.1214 |  |
| without_guidance | none | 34 | ok (saw it); receipt ok | 4/6 | skipped (objective-decided) | 0.1062 |  |
| with_guidance_full | full | 26582 | ok (saw it); receipt ok | 5/6 | 8.7 | 0.2517 |  |
| with_guidance_full_minus_section | full-minus-section | 25385 | ok (saw it); receipt ok | 5/6 | 8.3 | 0.2321 |  |
