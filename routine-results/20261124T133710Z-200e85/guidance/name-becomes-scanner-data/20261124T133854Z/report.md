# Eval report: guidance/name-becomes-scanner-data

- Modes: with_guidance_full=full, with_guidance_full_minus_section=full-minus-section
- Delivery: user
- Prompt: bundles/new-bundle/ holds a helper that provisions the site's deploy secrets. Pin it in bundles.lock with scripts/lock.py, under a short name that says what it is.
- Timestamp: 20261124T133854Z
- Run: billing subscription, runner routine, location cloud, id 20261124T133710Z-200e85; started 2026-11-24T13:38:54Z, ended 2026-11-24T13:39:32Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.08 to 0.08, from 4 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.35 over 4 call(s); agent $0.20, judge $0.00, guard $0.15; last agent call $0.10
- Estimated allowance (approximate, from token counts by type, weight table 2026-11-20): 0.02 points of the weekly meter (0.01 to 0.03); Fable meter 0.00 points
- Harness: Claude Code `2.1.331 (Claude Code)`; models used: with_guidance_full=claude-sonnet-5-5; with_guidance_full_minus_section=claude-sonnet-5-5

| Arm | Mode | Pair | Bytes | Guard | Objective | Judge overall | Cost (USD) | Error |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| with_guidance_full | full | in context | 26649 | ok (saw it); receipt ok | 3/3 | skipped: the full-guidance version passed more checks (3 of 3 vs 2 of 3) | 0.0962 |  |
| with_guidance_full_minus_section | full-minus-section | in context | 25646 | ok (saw it); receipt ok | 2/3 | skipped: the full-guidance version passed more checks (3 of 3 vs 2 of 3) | 0.1039 |  |

Judge: when the version with the skill or guidance passes more checks than its partner, the judge isn't needed and both are skipped. On a tie or a loss, the judge scores both from 0 to 10.
