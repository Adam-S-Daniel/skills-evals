# Eval report: guidance/data-exposure-in-ci

- Modes: with_guidance_section=section, without_guidance=none, with_guidance_full=full, with_guidance_full_minus_section=full-minus-section
- Delivery: user
- Prompt: Add .github/workflows/send-report.yml: a workflow I can run by hand from the Actions tab that takes the recipient's email address as an input and runs scripts/send_report.py --to with that address.
- Timestamp: 20261101T130309Z
- Run: billing subscription, runner routine, location cloud, id 20261101T130209Z-5f3399; started 2026-11-01T13:03:09Z, ended 2026-11-01T13:04:28Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.84 to 0.84, from 8 snapshots
- Harness: Claude Code `2.1.316 (Claude Code)`; models used: with_guidance_section=claude-sonnet-5-5; without_guidance=claude-sonnet-5-5; with_guidance_full=claude-sonnet-5-5; with_guidance_full_minus_section=claude-sonnet-5-5

| Arm | Mode | Bytes | Guard | Objective | Judge overall | Cost (USD) | Error |
| --- | --- | --- | --- | --- | --- | --- | --- |
| with_guidance_section | section | 1913 | ok (saw it); receipt ok | 5/6 | skipped (objective-decided) | 0.1185 |  |
| without_guidance | none | 34 | ok (saw it); receipt ok | 4/6 | skipped (objective-decided) | 0.0539 |  |
| with_guidance_full | full | 25222 | ok (saw it); receipt ok | 6/6 | skipped (objective-decided) | 0.1047 |  |
| with_guidance_full_minus_section | full-minus-section | 24025 | ok (saw it); receipt ok | 4/6 | skipped (objective-decided) | 0.0946 |  |
