# Eval report: guidance/anything-you-name-gets-its-link

- Modes: with_guidance_section=section, without_guidance=none, with_guidance_full=full, with_guidance_full_minus_section=full-minus-section
- Delivery: user
- Prompt: Write HANDOFF.md for whoever picks this up tomorrow: what is done, what is blocked and on what, and what comes next. STATUS.json has the state of things.
- Timestamp: 20261028T180512Z
- Run: billing subscription, runner routine, location cloud, id 20261028T180225Z-6c9c18; started 2026-10-28T18:05:12Z, ended 2026-10-28T18:06:33Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): five_hour 0.05 to 0.05, seven_day 0.32 to 0.32, from 8 snapshots
- Harness: Claude Code `2.1.312 (Claude Code)`; models used: with_guidance_section=claude-sonnet-5-5; without_guidance=claude-sonnet-5-5; with_guidance_full=claude-sonnet-5-5; with_guidance_full_minus_section=claude-sonnet-5-5

| Arm | Mode | Bytes | Guard | Objective | Judge overall | Cost (USD) | Error |
| --- | --- | --- | --- | --- | --- | --- | --- |
| with_guidance_section | section | 1495 | ok (saw it) | 4/4 | skipped (objective-decided) | 0.1197 |  |
| without_guidance | none | 34 | ok (saw it) | 0/4 | skipped (objective-decided) | 0.0607 |  |
| with_guidance_full | full | 25303 | ok (saw it) | 4/4 | skipped (objective-decided) | 0.1033 |  |
| with_guidance_full_minus_section | full-minus-section | 24383 | ok (saw it) | 0/4 | skipped (objective-decided) | 0.1052 |  |
