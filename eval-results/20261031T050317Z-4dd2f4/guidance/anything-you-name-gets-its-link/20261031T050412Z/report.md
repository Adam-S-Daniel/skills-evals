# Eval report: guidance/anything-you-name-gets-its-link

- Modes: with_guidance_section=section, without_guidance=none, with_guidance_full=full, with_guidance_full_minus_section=full-minus-section
- Delivery: user
- Prompt: Write DONE.md, a short summary of what landed this week, from STATUS.json.
- Timestamp: 20261031T050412Z
- Run: billing subscription, runner routine, location cloud, id 20261031T050317Z-4dd2f4; started 2026-10-31T05:04:12Z, ended 2026-10-31T05:05:20Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.67 to 0.68, from 8 snapshots
- Harness: Claude Code `2.1.314 (Claude Code)`; models used: with_guidance_section=claude-opus-5-5; without_guidance=claude-opus-5-5; with_guidance_full=claude-opus-5-5; with_guidance_full_minus_section=claude-opus-5-5

| Arm | Mode | Bytes | Guard | Objective | Judge overall | Cost (USD) | Error |
| --- | --- | --- | --- | --- | --- | --- | --- |
| with_guidance_section | section | 1602 | ok (saw it) | 3/3 | skipped (objective-decided) | 0.1193 |  |
| without_guidance | none | 34 | ok (saw it) | 0/3 | skipped (objective-decided) | 0.1047 |  |
| with_guidance_full | full | 25222 | ok (saw it) | 3/3 | skipped (objective-decided) | 0.1999 |  |
| with_guidance_full_minus_section | full-minus-section | 24336 | ok (saw it) | 0/3 | skipped (objective-decided) | 0.1880 |  |
