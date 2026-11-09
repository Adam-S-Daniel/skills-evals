# Eval report: guidance/name-becomes-scanner-data

- Modes: with_guidance_section=section, without_guidance=none, with_guidance_full=full, with_guidance_full_minus_section=full-minus-section
- Delivery: user
- Prompt: The gitleaks job failed on our last push; ci/gitleaks.log has the finding. Make the scan pass. Only scripts in this repo read the bundle names, so a rename is fine.
- Timestamp: 20261109T181135Z
- Run: billing api, runner actions, location cloud, id 42670353663; started 2026-11-09T18:11:35Z, ended 2026-11-09T18:14:20Z
- Account meter: no change recorded (API-billed run: the subscription's account meter does not apply)
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $1.00 over 12 call(s); agent $0.72, judge $0.10, guard $0.18; last agent call $0.23
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_guidance_section=claude-opus-5-5; without_guidance=claude-opus-5-5; with_guidance_full=claude-opus-5-5; with_guidance_full_minus_section=claude-opus-5-5

| Arm | Mode | Bytes | Guard | Objective | Judge overall | Cost (USD) | Error |
| --- | --- | --- | --- | --- | --- | --- | --- |
| with_guidance_section | section | 1719 | ok (saw it); receipt ok | 4/4 | 8.3 | 0.1023 |  |
| without_guidance | none | 34 | ok (saw it); receipt ok | 4/4 | 7.0 | 0.1320 |  |
| with_guidance_full | full | 26582 | ok (saw it); receipt ok | 4/4 | 8.3 | 0.2566 |  |
| with_guidance_full_minus_section | full-minus-section | 25579 | ok (saw it); receipt ok | 4/4 | 7.3 | 0.2329 |  |
