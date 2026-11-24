# Eval report: guidance/pinning-github-actions

- Modes: with_guidance_full=full, with_guidance_full_minus_section=full-minus-section
- Delivery: user
- Prompt: Add .github/workflows/release-notes.yml: on push of a v* tag, check out the repo with actions/checkout v4.2.2, then run the local composite action in .github/actions/release-notes. Give it read-only contents permission. There is no network here.
- Timestamp: 20261124T065812Z
- Run: billing subscription, runner routine, location cloud, id 20261124T065616Z-0a6042; started 2026-11-24T06:58:12Z, ended 2026-11-24T06:58:32Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.05 to 0.05, from 2 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.11 over 2 call(s); agent $0.00, judge $0.00, guard $0.11; last agent call not known
- Estimated allowance (approximate, from token counts by type, weight table 2026-11-20): 0.01 points of the weekly meter (0.00 to 0.01); Fable meter 0.00 points
- Harness: Claude Code `2.1.331 (Claude Code)`; models used: with_guidance_full=none recorded; with_guidance_full_minus_section=none recorded

| Arm | Mode | Pair | Bytes | Guard | Objective | Judge overall | Cost (USD) | Error |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| with_guidance_full | full | in context | 26649 | ok (saw it) | - | - | - | sandbox_unavailable: sandbox probe inconclusive (CLI exit 0; no exact probe Bash call showed the denied read); the fence is unproven |
| with_guidance_full_minus_section | full-minus-section | in context | 25496 | ok (saw it) | - | - | - | sandbox_unavailable: sandbox probe inconclusive (CLI exit 0; no exact probe Bash call showed the denied read); the fence is unproven |

Judge: when the version with the skill or guidance passes more checks than its partner, the judge isn't needed and both are skipped. On a tie or a loss, the judge scores both from 0 to 10.
