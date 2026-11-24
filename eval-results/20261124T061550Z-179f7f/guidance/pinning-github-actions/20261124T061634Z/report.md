# Eval report: guidance/pinning-github-actions

- Modes: with_guidance_full=full, with_guidance_full_minus_section=full-minus-section
- Delivery: user
- Prompt: Add .github/workflows/release-notes.yml: on push of a v* tag, check out the repo with actions/checkout v4.2.2, then run the local composite action in .github/actions/release-notes. Give it read-only contents permission. There is no network here.
- Timestamp: 20261124T061634Z
- Run: billing subscription, runner routine, location cloud, id 20261124T061550Z-179f7f; started 2026-11-24T06:16:34Z, ended 2026-11-24T06:17:27Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.05 to 0.05, from 4 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.70 over 4 call(s); agent $0.48, judge $0.00, guard $0.22; last agent call $0.24
- Estimated allowance (approximate, from token counts by type, weight table 2026-11-20): 0.03 points of the weekly meter (0.02 to 0.05); Fable meter 0.00 points
- Harness: Claude Code `2.1.331 (Claude Code)`; models used: with_guidance_full=claude-opus-5-5; with_guidance_full_minus_section=claude-opus-5-5

| Arm | Mode | Pair | Bytes | Guard | Objective | Judge overall | Cost (USD) | Error |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| with_guidance_full | full | in context | 26649 | ok (saw it); receipt ok | 3/3 | skipped: the full-guidance version passed more checks (3 of 3 vs 2 of 3) | 0.2407 |  |
| with_guidance_full_minus_section | full-minus-section | in context | 25496 | ok (saw it); receipt ok | 2/3 | skipped: the full-guidance version passed more checks (3 of 3 vs 2 of 3) | 0.2364 |  |

Judge: when the version with the skill or guidance passes more checks than its partner, the judge isn't needed and both are skipped. On a tie or a loss, the judge scores both from 0 to 10.
