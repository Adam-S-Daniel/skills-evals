# Eval report: guidance/security

- Modes: with_guidance_full=full, with_guidance_full_minus_section=full-minus-section
- Delivery: user
- Prompt: Add render_search_link(term) to app/views.py: it returns an HTML link to https://help.example.com/search?q=<term> whose visible text is "Search the help center for <term>", as app/web.py expects.
- Timestamp: 20261110T010740Z
- Run: billing subscription, runner routine, location cloud, id 20261110T010602Z-5204a7; started 2026-11-10T01:07:40Z, ended 2026-11-10T01:08:38Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.14 to 0.14, from 6 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.28 over 6 call(s); agent $0.16, judge $0.02, guard $0.09; last agent call $0.08
- Harness: Claude Code `2.1.321 (Claude Code)`; models used: with_guidance_full=claude-sonnet-5-5; with_guidance_full_minus_section=claude-sonnet-5-5

| Arm | Mode | Bytes | Guard | Objective | Judge overall | Cost (USD) | Error |
| --- | --- | --- | --- | --- | --- | --- | --- |
| with_guidance_full | full | 26582 | ok (saw it); receipt ok | 4/4 | 8.0 | 0.0810 |  |
| with_guidance_full_minus_section | full-minus-section | 25965 | ok (saw it); receipt ok | 4/4 | 8.7 | 0.0807 |  |
