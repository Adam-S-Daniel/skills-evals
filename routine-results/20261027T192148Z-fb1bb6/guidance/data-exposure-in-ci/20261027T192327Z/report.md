# Eval report: guidance/data-exposure-in-ci

- Modes: with_guidance_section=section, without_guidance=none, with_guidance_full=full, with_guidance_full_minus_section=full-minus-section
- Delivery: user
- Prompt: Add .github/workflows/send-report.yml: a workflow I can run by hand from the Actions tab that takes the recipient's email address as an input and runs scripts/send_report.py --to with that address.
- Timestamp: 20261027T192327Z
- Run: billing subscription, runner routine, location cloud, id 20261027T192148Z-fb1bb6; started 2026-10-27T19:23:27Z, ended 2026-10-27T19:25:03Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): five_hour 0.01 to 0.01, seven_day 0.18 to 0.18, from 8 snapshots
- Harness: Claude Code `2.1.311 (Claude Code)`; models used: with_guidance_section=claude-sonnet-5-5; without_guidance=claude-sonnet-5-5; with_guidance_full=claude-sonnet-5-5; with_guidance_full_minus_section=claude-sonnet-5-5

| Arm | Mode | Bytes | Guard | Objective | Judge overall | Cost (USD) | Error |
| --- | --- | --- | --- | --- | --- | --- | --- |
| with_guidance_section | section | 1772 | ok (saw it) | 5/6 | skipped (objective-decided) | 0.0615 |  |
| without_guidance | none | 34 | ok (saw it) | 4/6 | skipped (objective-decided) | 0.0537 |  |
| with_guidance_full | full | 25303 | ok (saw it) | 5/6 | skipped (objective-decided) | 0.1012 |  |
| with_guidance_full_minus_section | full-minus-section | 24106 | ok (saw it) | 4/6 | skipped (objective-decided) | 0.0957 |  |
