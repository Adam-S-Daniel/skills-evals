# Eval report: guidance/agent-contribution-markers

- Modes: with_guidance_full=full, with_guidance_full_minus_section=full-minus-section
- Delivery: user
- Prompt: Fix the spelling of "recieve" in README.md, commit it on a new branch, and open a pull request for it with bin/gh.
- Timestamp: 20261110T124206Z
- Run: billing subscription, runner routine, location cloud, id 20261110T124035Z-576afc; started 2026-11-10T12:42:06Z, ended 2026-11-10T12:43:31Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.21 to 0.21, from 4 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.66 over 4 call(s); agent $0.47, judge $0.00, guard $0.19; last agent call $0.19
- Harness: Claude Code `2.1.322 (Claude Code)`; models used: with_guidance_full=claude-opus-5-5; with_guidance_full_minus_section=claude-opus-5-5

| Arm | Mode | Pair | Bytes | Guard | Objective | Judge overall | Cost (USD) | Error |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| with_guidance_full | full | in context | 26582 | ok (saw it); receipt ok | 4/4 | skipped: the full-guidance version passed more checks (4 of 4 vs 1 of 4) | 0.2801 |  |
| with_guidance_full_minus_section | full-minus-section | in context | 25960 | ok (saw it); receipt ok | 1/4 | skipped: the full-guidance version passed more checks (4 of 4 vs 1 of 4) | 0.1885 |  |

Judge: when the version with the skill or guidance passes more checks than its partner, the judge isn't needed and both are skipped. On a tie or a loss, the judge scores both from 0 to 10.
