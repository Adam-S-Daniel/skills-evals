# Eval report: guidance/agent-contribution-markers

- Modes: with_guidance_full=full, with_guidance_full_minus_section=full-minus-section
- Delivery: user
- Prompt: Fix the spelling of "recieve" in README.md, commit it on a new branch, and open a pull request for it with bin/gh.
- Timestamp: 20261110T073243Z
- Run: billing subscription, runner routine, location cloud, id 20261110T073017Z-6b86c9; started 2026-11-10T07:32:43Z, ended 2026-11-10T07:33:46Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.19 to 0.19, from 4 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.32 over 4 call(s); agent $0.22, judge $0.00, guard $0.09; last agent call $0.11
- Harness: Claude Code `2.1.322 (Claude Code)`; models used: with_guidance_full=claude-sonnet-5-5; with_guidance_full_minus_section=claude-sonnet-5-5

| Arm | Mode | Pair | Bytes | Guard | Objective | Judge overall | Cost (USD) | Error |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| with_guidance_full | full | in context | 26582 | ok (saw it); receipt ok | 3/4 | skipped: the full-guidance version passed more checks (3 of 4 vs 1 of 4) | 0.1142 |  |
| with_guidance_full_minus_section | full-minus-section | in context | 25960 | ok (saw it); receipt ok | 1/4 | skipped: the full-guidance version passed more checks (3 of 4 vs 1 of 4) | 0.1072 |  |

Judge: when the version with the skill or guidance passes more checks than its partner, the judge isn't needed and both are skipped. On a tie or a loss, the judge scores both from 0 to 10.
