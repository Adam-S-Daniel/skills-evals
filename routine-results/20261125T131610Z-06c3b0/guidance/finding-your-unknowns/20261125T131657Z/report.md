# Eval report: guidance/finding-your-unknowns

- Modes: with_guidance_full=full, with_guidance_full_minus_section=full-minus-section
- Delivery: user
- Prompt: Agents in every one of our repositories keep telling me a CI run passed when all they saw was their watch command finish. Make sure agents across the fleet stop doing that.
- Timestamp: 20261125T131657Z
- Run: billing subscription, runner routine, location cloud, id 20261125T131610Z-06c3b0; started 2026-11-25T13:16:57Z, ended 2026-11-25T13:18:08Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.18 to 0.18, from 6 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.44 over 6 call(s); agent $0.27, judge $0.06, guard $0.11; last agent call $0.13
- Estimated allowance (approximate, from token counts by type, weight table 2026-11-20): 0.02 points of the weekly meter (0.02 to 0.04); Fable meter 0.00 points
- Harness: Claude Code `2.1.332 (Claude Code)`; models used: with_guidance_full=claude-sonnet-5-5; with_guidance_full_minus_section=claude-sonnet-5-5

| Arm | Mode | Pair | Bytes | Guard | Objective | Judge overall | Cost (USD) | Error |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| with_guidance_full | full | in context | 26649 | ok (saw it); receipt ok | 3/3 | 9.3 | 0.1381 |  |
| with_guidance_full_minus_section | full-minus-section | in context | 25634 | ok (saw it); receipt ok | 3/3 | 9.7 | 0.1283 |  |

Judge: when the version with the skill or guidance passes more checks than its partner, the judge isn't needed and both are skipped. On a tie or a loss, the judge scores both from 0 to 10.
