# Eval report: guidance/name-becomes-scanner-data

- Modes: with_guidance_section=section, without_guidance=none, with_guidance_full=full, with_guidance_full_minus_section=full-minus-section
- Delivery: user
- Prompt: The gitleaks job failed on our last push; ci/gitleaks.log has the finding. Make the scan pass. Only scripts in this repo read the bundle names, so a rename is fine.
- Timestamp: 20261109T230034Z
- Run: billing api, runner actions, location cloud, id 42712126963; started 2026-11-09T23:00:34Z, ended 2026-11-09T23:01:59Z
- Account meter: no change recorded (API-billed run: the subscription's account meter does not apply)
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.42 over 12 call(s); agent $0.25, judge $0.09, guard $0.09; last agent call $0.08
- Harness: Claude Code `2.1.321 (Claude Code)`; models used: with_guidance_section=claude-sonnet-5-5; without_guidance=claude-sonnet-5-5; with_guidance_full=claude-sonnet-5-5; with_guidance_full_minus_section=claude-sonnet-5-5

| Arm | Mode | Bytes | Guard | Objective | Judge overall | Cost (USD) | Error |
| --- | --- | --- | --- | --- | --- | --- | --- |
| with_guidance_section | section | 1719 | ok (saw it); receipt ok | 4/4 | 8.7 | 0.0470 |  |
| without_guidance | none | 34 | ok (saw it); receipt ok | 4/4 | 9.0 | 0.0485 |  |
| with_guidance_full | full | 26582 | ok (saw it); receipt ok | 4/4 | 9.0 | 0.0736 |  |
| with_guidance_full_minus_section | full-minus-section | 25579 | ok (saw it); receipt ok | 4/4 | 9.3 | 0.0770 |  |
