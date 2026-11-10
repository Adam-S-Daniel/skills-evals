# Eval report: guidance/pinning-github-actions

- Modes: with_guidance_full=full, with_guidance_full_minus_section=full-minus-section
- Delivery: user
- Prompt: Add .github/workflows/release-notes.yml: on push of a v* tag, check out the repo with actions/checkout v4.2.2, then run the local composite action in .github/actions/release-notes. Give it read-only contents permission. There is no network here.
- Timestamp: 20261110T185405Z
- Run: billing subscription, runner routine, location cloud, id 20261110T185214Z-2a0d65; started 2026-11-10T18:54:05Z, ended 2026-11-10T18:55:03Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.26 to 0.26, from 4 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.62 over 4 call(s); agent $0.43, judge $0.00, guard $0.19; last agent call $0.17
- Harness: Claude Code `2.1.322 (Claude Code)`; models used: with_guidance_full=claude-opus-5-5; with_guidance_full_minus_section=claude-opus-5-5

| Arm | Mode | Pair | Bytes | Guard | Objective | Judge overall | Cost (USD) | Error |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| with_guidance_full | full | in context | 26582 | ok (saw it); receipt ok | 3/3 | skipped: the full-guidance version passed more checks (3 of 3 vs 2 of 3) | 0.2677 |  |
| with_guidance_full_minus_section | full-minus-section | in context | 25429 | ok (saw it); receipt ok | 2/3 | skipped: the full-guidance version passed more checks (3 of 3 vs 2 of 3) | 0.1669 |  |

Judge: when the version with the skill or guidance passes more checks than its partner, the judge isn't needed and both are skipped. On a tie or a loss, the judge scores both from 0 to 10.
