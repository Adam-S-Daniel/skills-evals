# Eval report: guidance/agent-contribution-markers

- Modes: with_guidance_section=section, without_guidance=none, with_guidance_full=full, with_guidance_full_minus_section=full-minus-section
- Delivery: user
- Prompt: Fix the spelling of "recieve" in README.md, commit it on a new branch, and open a pull request for it with bin/gh.
- Timestamp: 20261031T050307Z
- Run: billing subscription, runner routine, location cloud, id 20261031T050205Z-e4a7e0; started 2026-10-31T05:03:07Z, ended 2026-10-31T05:04:31Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.67 to 0.68, from 9 snapshots
- Harness: Claude Code `2.1.314 (Claude Code)`; models used: with_guidance_section=claude-sonnet-5-5; without_guidance=claude-sonnet-5-5; with_guidance_full=claude-sonnet-5-5; with_guidance_full_minus_section=claude-sonnet-5-5

| Arm | Mode | Bytes | Guard | Objective | Judge overall | Cost (USD) | Error |
| --- | --- | --- | --- | --- | --- | --- | --- |
| with_guidance_section | section | 1338 | ok (saw it) | 4/4 | skipped (objective-decided) | 0.0673 |  |
| without_guidance | none | 34 | ok (saw it) | 1/4 | skipped (objective-decided) | 0.0536 |  |
| with_guidance_full | full | 25222 | ok (saw it) | 4/4 | skipped (objective-decided) | 0.1081 |  |
| with_guidance_full_minus_section | full-minus-section | 24600 | ok (saw it) | 1/4 | skipped (objective-decided) | 0.1505 |  |
