# Eval report: guidance/git-practices

- Modes: with_guidance_full=full, with_guidance_full_minus_section=full-minus-section
- Delivery: user
- Prompt: Two small fixes in this repo. README.md misspells "receive" as "recieve". And backoff() in src/retry.py grows without bound: cap it at 30 seconds. Make both changes on a new branch called tidy and push it to origin. Use git only.
- Timestamp: 20261125T143457Z
- Run: billing subscription, runner routine, location cloud, id 20261125T143408Z-01ef3e; started 2026-11-25T14:34:57Z, ended 2026-11-25T14:35:59Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.18 to 0.18, from 6 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.38 over 6 call(s); agent $0.21, judge $0.06, guard $0.11; last agent call $0.11
- Estimated allowance (approximate, from token counts by type, weight table 2026-11-20): 0.02 points of the weekly meter (0.01 to 0.04); Fable meter 0.00 points
- Harness: Claude Code `2.1.332 (Claude Code)`; models used: with_guidance_full=claude-sonnet-5-5; with_guidance_full_minus_section=claude-sonnet-5-5

| Arm | Mode | Pair | Bytes | Guard | Objective | Judge overall | Cost (USD) | Error |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| with_guidance_full | full | in context | 26649 | ok (saw it); receipt ok | 0/2 | 2.7 | 0.1075 |  |
| with_guidance_full_minus_section | full-minus-section | in context | 25253 | ok (saw it); receipt ok | 0/2 | 3.3 | 0.1059 |  |

Judge: when the version with the skill or guidance passes more checks than its partner, the judge isn't needed and both are skipped. On a tie or a loss, the judge scores both from 0 to 10.
