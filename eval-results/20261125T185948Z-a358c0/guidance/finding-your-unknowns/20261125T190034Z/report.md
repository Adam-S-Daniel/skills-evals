# Eval report: guidance/finding-your-unknowns

- Modes: with_guidance_full=full, with_guidance_full_minus_section=full-minus-section
- Delivery: user
- Prompt: Agents in every one of our repositories keep telling me a CI run passed when all they saw was their watch command finish. Make sure agents across the fleet stop doing that.
- Timestamp: 20261125T190034Z
- Run: billing subscription, runner routine, location cloud, id 20261125T185948Z-a358c0; started 2026-11-25T19:00:34Z, ended 2026-11-25T19:02:54Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.19 to 0.19, from 6 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $1.31 over 6 call(s); agent $0.93, judge $0.07, guard $0.31; last agent call $0.39
- Estimated allowance (approximate, from token counts by type, weight table 2026-11-20): 0.06 points of the weekly meter (0.04 to 0.09); Fable meter 0.00 points
- Harness: Claude Code `2.1.332 (Claude Code)`; models used: with_guidance_full=claude-opus-5-5; with_guidance_full_minus_section=claude-opus-5-5

| Arm | Mode | Pair | Bytes | Guard | Objective | Judge overall | Cost (USD) | Error |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| with_guidance_full | full | in context | 26649 | ok (saw it); receipt ok | 3/3 | 10.0 | 0.5340 |  |
| with_guidance_full_minus_section | full-minus-section | in context | 25634 | ok (saw it); receipt ok | 3/3 | 9.3 | 0.3939 |  |

Judge: when the version with the skill or guidance passes more checks than its partner, the judge isn't needed and both are skipped. On a tie or a loss, the judge scores both from 0 to 10.
