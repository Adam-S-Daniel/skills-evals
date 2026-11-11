# Eval report: guidance/data-exposure-in-ci

- Modes: with_guidance_full=full, with_guidance_full_minus_section=full-minus-section
- Delivery: user
- Prompt: Add .github/workflows/send-report.yml: a workflow I can run by hand from the Actions tab that takes the recipient's email address as an input and runs scripts/send_report.py --to with that address.
- Timestamp: 20261111T103341Z
- Run: billing subscription, runner routine, location cloud, id 20261111T103122Z-d51d91; started 2026-11-11T10:33:41Z, ended 2026-11-11T10:34:34Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.33 to 0.33, from 4 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.29 over 4 call(s); agent $0.19, judge $0.00, guard $0.09; last agent call $0.08
- Harness: Claude Code `2.1.322 (Claude Code)`; models used: with_guidance_full=claude-sonnet-5-5; with_guidance_full_minus_section=claude-sonnet-5-5

| Arm | Mode | Pair | Bytes | Guard | Objective | Judge overall | Cost (USD) | Error |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| with_guidance_full | full | in context | 26582 | ok (saw it); receipt ok | 5/6 | skipped: the full-guidance version passed more checks (5 of 6 vs 4 of 6) | 0.1109 |  |
| with_guidance_full_minus_section | full-minus-section | in context | 25385 | ok (saw it); receipt ok | 4/6 | skipped: the full-guidance version passed more checks (5 of 6 vs 4 of 6) | 0.0832 |  |

Judge: when the version with the skill or guidance passes more checks than its partner, the judge isn't needed and both are skipped. On a tie or a loss, the judge scores both from 0 to 10.
