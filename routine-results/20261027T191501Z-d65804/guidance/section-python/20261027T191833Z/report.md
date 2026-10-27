# Eval report: guidance/section-python

- Modes: with_guidance_section=section, without_guidance=none, with_guidance_full=full, with_guidance_full_minus_section=full-minus-section
- Delivery: user
- Prompt: Add load_settings(path) to settings.py: it reads a JSON file of overrides and returns merged(overrides). If the file is missing or is not valid JSON, report it and return the defaults.
- Timestamp: 20261027T191833Z
- Run: billing subscription, runner routine, location cloud, id 20261027T191501Z-d65804; started 2026-10-27T19:18:33Z, ended 2026-10-27T19:20:24Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): five_hour 0.15 to 0, seven_day 0.17 to 0.17, from 10 snapshots
- Harness: Claude Code `2.1.311 (Claude Code)`; models used: with_guidance_section=claude-sonnet-5-5; without_guidance=claude-sonnet-5-5; with_guidance_full=claude-sonnet-5-5; with_guidance_full_minus_section=claude-sonnet-5-5

| Arm | Mode | Bytes | Guard | Objective | Judge overall | Cost (USD) | Error |
| --- | --- | --- | --- | --- | --- | --- | --- |
| with_guidance_section | section | 820 | ok (saw it) | 4/4 | skipped (objective-decided) | 0.1121 |  |
| without_guidance | none | 34 | ok (saw it) | 3/4 | skipped (objective-decided) | 0.0522 |  |
| with_guidance_full | full | 26089 | ok (saw it) | 4/4 | skipped (objective-decided) | 0.1173 |  |
| with_guidance_full_minus_section | full-minus-section | 25303 | ok (saw it) | 3/4 | skipped (objective-decided) | 0.1233 |  |
