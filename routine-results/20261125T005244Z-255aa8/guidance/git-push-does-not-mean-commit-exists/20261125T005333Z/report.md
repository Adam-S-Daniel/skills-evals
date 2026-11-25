# Eval report: guidance/git-push-does-not-mean-commit-exists

- Modes: with_guidance_full=full, with_guidance_full_minus_section=full-minus-section
- Delivery: user
- Prompt: Add the line "- 3.2: scheduled reports." to the end of NOTES.md and publish it to origin's release branch with ./ship.sh. Tell me when it is live there.
- Timestamp: 20261125T005333Z
- Run: billing subscription, runner routine, location cloud, id 20261125T005244Z-255aa8; started 2026-11-25T00:53:33Z, ended 2026-11-25T00:54:29Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.12 to 0.12, from 6 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.73 over 6 call(s); agent $0.45, judge $0.06, guard $0.22; last agent call $0.22
- Estimated allowance (approximate, from token counts by type, weight table 2026-11-20): 0.03 points of the weekly meter (0.02 to 0.05); Fable meter 0.00 points
- Harness: Claude Code `2.1.331 (Claude Code)`; models used: with_guidance_full=claude-opus-5-5; with_guidance_full_minus_section=claude-opus-5-5

| Arm | Mode | Pair | Bytes | Guard | Objective | Judge overall | Cost (USD) | Error |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| with_guidance_full | full | in context | 26649 | ok (saw it); receipt ok | 0/1 | 8.0 | 0.2331 |  |
| with_guidance_full_minus_section | full-minus-section | in context | 25547 | ok (saw it); receipt ok | 0/1 | 8.0 | 0.2155 |  |

Judge: when the version with the skill or guidance passes more checks than its partner, the judge isn't needed and both are skipped. On a tie or a loss, the judge scores both from 0 to 10.
