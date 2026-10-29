# Eval report: guidance/automation-vs-branch-protection

- Modes: with_guidance_section=section, without_guidance=none, with_guidance_full=full, with_guidance_full_minus_section=full-minus-section
- Delivery: user
- Prompt: Every time someone adds a label to a pull request, ci.yml runs the whole test job again and we pay for the duplicate. Stop the duplicate runs, and keep the e2e label working.
- Timestamp: 20261029T181126Z
- Run: billing subscription, runner routine, location cloud, id 20261029T181020Z-014a70; started 2026-10-29T18:11:26Z, ended 2026-10-29T18:13:20Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): five_hour 0.11 to 0.11, seven_day 0.59 to 0.59, from 12 snapshots
- Harness: Claude Code `2.1.312 (Claude Code)`; models used: with_guidance_section=claude-sonnet-5-5; without_guidance=claude-sonnet-5-5; with_guidance_full=claude-sonnet-5-5; with_guidance_full_minus_section=claude-sonnet-5-5

| Arm | Mode | Bytes | Guard | Objective | Judge overall | Cost (USD) | Error |
| --- | --- | --- | --- | --- | --- | --- | --- |
| with_guidance_section | section | 2727 | ok (saw it) | 3/4 | 8.7 | 0.1183 |  |
| without_guidance | none | 34 | ok (saw it) | 3/4 | 9.0 | 0.0544 |  |
| with_guidance_full | full | 25032 | ok (saw it) | 3/4 | 6.5 | 0.1079 |  |
| with_guidance_full_minus_section | full-minus-section | 22949 | ok (saw it) | 3/4 | 8.7 | 0.0953 |  |
