# Eval report: guidance/security

- Modes: with_guidance_full=full, with_guidance_full_minus_section=full-minus-section
- Delivery: user
- Prompt: Add render_search_link(term) to app/views.py: it returns an HTML link to https://help.example.com/search?q=<term> whose visible text is "Search the help center for <term>", as app/web.py expects.
- Timestamp: 20261124T225637Z
- Run: billing subscription, runner routine, location cloud, id 20261124T225446Z-cf0ea4; started 2026-11-24T22:56:37Z, ended 2026-11-24T22:57:28Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.12 to 0.12, from 6 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.39 over 6 call(s); agent $0.22, judge $0.06, guard $0.11; last agent call $0.10
- Estimated allowance (approximate, from token counts by type, weight table 2026-11-20): 0.02 points of the weekly meter (0.01 to 0.04); Fable meter 0.00 points
- Harness: Claude Code `2.1.331 (Claude Code)`; models used: with_guidance_full=claude-sonnet-5-5; with_guidance_full_minus_section=claude-sonnet-5-5

| Arm | Mode | Pair | Bytes | Guard | Objective | Judge overall | Cost (USD) | Error |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| with_guidance_full | full | in context | 26649 | ok (saw it); receipt ok | 4/4 | 9.7 | 0.1226 |  |
| with_guidance_full_minus_section | full-minus-section | in context | 26032 | ok (saw it); receipt ok | 4/4 | 9.0 | 0.0982 |  |

Judge: when the version with the skill or guidance passes more checks than its partner, the judge isn't needed and both are skipped. On a tie or a loss, the judge scores both from 0 to 10.
