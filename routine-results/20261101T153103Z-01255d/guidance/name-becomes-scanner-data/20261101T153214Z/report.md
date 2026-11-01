# Eval report: guidance/name-becomes-scanner-data

- Modes: with_guidance_section=section, without_guidance=none, with_guidance_full=full, with_guidance_full_minus_section=full-minus-section
- Delivery: user
- Prompt: bundles/new-bundle/ holds a helper that provisions the site's deploy secrets. Pin it in bundles.lock with scripts/lock.py, under a short name that says what it is.
- Timestamp: 20261101T153214Z
- Run: billing subscription, runner routine, location cloud, id 20261101T153103Z-01255d; started 2026-11-01T15:32:14Z, ended 2026-11-01T15:33:25Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.87 to 0.87, from 8 snapshots
- Harness: Claude Code `2.1.316 (Claude Code)`; models used: with_guidance_section=claude-sonnet-5-5; without_guidance=claude-sonnet-5-5; with_guidance_full=claude-sonnet-5-5; with_guidance_full_minus_section=claude-sonnet-5-5

| Arm | Mode | Bytes | Guard | Objective | Judge overall | Cost (USD) | Error |
| --- | --- | --- | --- | --- | --- | --- | --- |
| with_guidance_section | section | 1719 | ok (saw it); receipt ok | 3/3 | skipped (objective-decided) | 0.1078 |  |
| without_guidance | none | 34 | ok (saw it); receipt ok | 2/3 | skipped (objective-decided) | 0.0468 |  |
| with_guidance_full | full | 25222 | ok (saw it); receipt ok | 3/3 | skipped (objective-decided) | 0.0996 |  |
| with_guidance_full_minus_section | full-minus-section | 24219 | ok (saw it); receipt ok | 2/3 | skipped (objective-decided) | 0.1013 |  |
