# Eval report: guidance/git-practices

- Modes: with_guidance_full=full, with_guidance_full_minus_section=full-minus-section
- Delivery: user
- Prompt: The latest commit on fix-retry, "Fix retyr count", has a typo in its message, and the branch is already on origin with its pull request open. Make the history read "retry" and get that onto origin. Use git only.
- Timestamp: 20261125T070748Z
- Run: billing subscription, runner routine, location cloud, id 20261125T070705Z-ba077d; started 2026-11-25T07:07:48Z, ended 2026-11-25T07:08:31Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.15 to 0.15, from 6 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.39 over 6 call(s); agent $0.19, judge $0.05, guard $0.15; last agent call $0.09
- Estimated allowance (approximate, from token counts by type, weight table 2026-11-20): 0.02 points of the weekly meter (0.01 to 0.04); Fable meter 0.00 points
- Harness: Claude Code `2.1.332 (Claude Code)`; models used: with_guidance_full=claude-sonnet-5-5; with_guidance_full_minus_section=claude-sonnet-5-5

| Arm | Mode | Pair | Bytes | Guard | Objective | Judge overall | Cost (USD) | Error |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| with_guidance_full | full | in context | 26649 | ok (saw it); receipt ok | 0/1 | 3.5 | 0.0950 |  |
| with_guidance_full_minus_section | full-minus-section | in context | 25253 | ok (saw it); receipt ok | 0/1 | 3.0 | 0.0911 |  |

Judge: when the version with the skill or guidance passes more checks than its partner, the judge isn't needed and both are skipped. On a tie or a loss, the judge scores both from 0 to 10.
