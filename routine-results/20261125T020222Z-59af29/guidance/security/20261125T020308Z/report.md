# Eval report: guidance/security

- Modes: with_guidance_full=full, with_guidance_full_minus_section=full-minus-section
- Delivery: user
- Prompt: Add render_search_link(term) to app/views.py: it returns an HTML link to https://help.example.com/search?q=<term> whose visible text is "Search the help center for <term>", as app/web.py expects.
- Timestamp: 20261125T020308Z
- Run: billing subscription, runner routine, location cloud, id 20261125T020222Z-59af29; started 2026-11-25T02:03:08Z, ended 2026-11-25T02:03:26Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.13 to 0.13, from 2 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.22 over 2 call(s); agent $0.00, judge $0.00, guard $0.22; last agent call not known
- Estimated allowance (approximate, from token counts by type, weight table 2026-11-20): 0.01 points of the weekly meter (0.00 to 0.01); Fable meter 0.00 points
- Harness: Claude Code `2.1.332 (Claude Code)`; models used: with_guidance_full=none recorded; with_guidance_full_minus_section=none recorded

| Arm | Mode | Pair | Bytes | Guard | Objective | Judge overall | Cost (USD) | Error |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| with_guidance_full | full | in context | 26649 | ok (saw it) | - | - | - | sandbox_unavailable: sandbox probe inconclusive (CLI exit 0; no exact probe Bash call showed the denied read); the fence is unproven |
| with_guidance_full_minus_section | full-minus-section | in context | 26032 | ok (saw it) | - | - | - | sandbox_unavailable: sandbox probe inconclusive (CLI exit 0; no exact probe Bash call showed the denied read); the fence is unproven |

Judge: when the version with the skill or guidance passes more checks than its partner, the judge isn't needed and both are skipped. On a tie or a loss, the judge scores both from 0 to 10.
