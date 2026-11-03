# Eval report: guidance/dependency-updates

- Modes: with_guidance_section=section, without_guidance=none, with_guidance_full=full, with_guidance_full_minus_section=full-minus-section
- Delivery: user
- Prompt: Add a Dependabot config that keeps this repository's npm packages and its GitHub Actions up to date, checking weekly.
- Timestamp: 20261103T190131Z
- Run: billing subscription, runner routine, location cloud, id 20261103T184857Z-307da1; started 2026-11-03T19:01:31Z, ended 2026-11-03T19:02:35Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.67 to 0.67, from 8 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.47 over 8 call(s); agent $0.29, judge $0.00, guard $0.17; last agent call $0.10
- Harness: Claude Code `2.1.317 (Claude Code)`; models used: with_guidance_section=claude-sonnet-5-5; without_guidance=claude-sonnet-5-5; with_guidance_full=claude-sonnet-5-5; with_guidance_full_minus_section=claude-sonnet-5-5

| Arm | Mode | Bytes | Guard | Objective | Judge overall | Cost (USD) | Error |
| --- | --- | --- | --- | --- | --- | --- | --- |
| with_guidance_section | section | 1250 | ok (saw it); receipt ok | 4/4 | skipped (objective-decided) | 0.0547 |  |
| without_guidance | none | 34 | ok (saw it); receipt ok | 2/4 | skipped (objective-decided) | 0.0458 |  |
| with_guidance_full | full | 25562 | ok (saw it); receipt ok | 4/4 | skipped (objective-decided) | 0.0970 |  |
| with_guidance_full_minus_section | full-minus-section | 25028 | ok (saw it); receipt ok | 2/4 | skipped (objective-decided) | 0.0953 |  |
