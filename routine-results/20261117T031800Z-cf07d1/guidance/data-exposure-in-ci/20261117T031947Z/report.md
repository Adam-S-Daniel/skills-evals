# Eval report: guidance/data-exposure-in-ci

- Modes: with_guidance_full=full, with_guidance_full_minus_section=full-minus-section
- Delivery: user
- Prompt: Add .github/workflows/send-report.yml: a workflow I can run by hand from the Actions tab that takes the recipient's email address as an input and runs scripts/send_report.py --to with that address.
- Timestamp: 20261117T031947Z
- Run: billing subscription, runner routine, location cloud, id 20261117T031800Z-cf07d1; started 2026-11-17T03:19:47Z, ended 2026-11-17T03:20:18Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.06 to 0.06, from 4 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.21 over 4 call(s); agent $0.14, judge $0.00, guard $0.07; last agent call $0.07
- Harness: Claude Code `2.1.326 (Claude Code)`; models used: with_guidance_full=claude-sonnet-5-5; with_guidance_full_minus_section=claude-sonnet-5-5

| Arm | Mode | Pair | Bytes | Guard | Objective | Judge overall | Cost (USD) | Error |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| with_guidance_full | full | in context | 26653 | ok (saw it); receipt ok | 5/6 | skipped: the full-guidance version passed more checks (5 of 6 vs 4 of 6) | 0.0697 |  |
| with_guidance_full_minus_section | full-minus-section | in context | 25456 | ok (saw it); receipt ok | 4/6 | skipped: the full-guidance version passed more checks (5 of 6 vs 4 of 6) | 0.0676 |  |

Judge: when the version with the skill or guidance passes more checks than its partner, the judge isn't needed and both are skipped. On a tie or a loss, the judge scores both from 0 to 10.
