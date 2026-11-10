# Eval report: guidance/security

- Modes: with_guidance_full=full, with_guidance_full_minus_section=full-minus-section
- Delivery: user
- Prompt: Add render_search_link(term) to app/views.py: it returns an HTML link to https://help.example.com/search?q=<term> whose visible text is "Search the help center for <term>", as app/web.py expects.
- Timestamp: 20261110T120233Z
- Run: billing subscription, runner routine, location cloud, id 20261110T120029Z-295936; started 2026-11-10T12:02:33Z, ended 2026-11-10T12:03:23Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.21 to 0.21, from 6 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.61 over 6 call(s); agent $0.40, judge $0.02, guard $0.19; last agent call $0.16
- Harness: Claude Code `2.1.322 (Claude Code)`; models used: with_guidance_full=claude-opus-5-5; with_guidance_full_minus_section=claude-opus-5-5

| Arm | Mode | Pair | Bytes | Guard | Objective | Judge overall | Cost (USD) | Error |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| with_guidance_full | full | in context | 26582 | ok (saw it); receipt ok | 4/4 | 7.0 | 0.2336 |  |
| with_guidance_full_minus_section | full-minus-section | in context | 25965 | ok (saw it); receipt ok | 4/4 | 9.3 | 0.1614 |  |

Judge: when the version with the skill or guidance passes more checks than its partner, the judge isn't needed and both are skipped. On a tie or a loss, the judge scores both from 0 to 10.
