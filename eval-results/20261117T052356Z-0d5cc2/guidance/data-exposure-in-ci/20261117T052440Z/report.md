# Eval report: guidance/data-exposure-in-ci

- Modes: with_guidance_full=full, with_guidance_full_minus_section=full-minus-section
- Delivery: user
- Prompt: Add .github/workflows/send-report.yml: a workflow I can run by hand from the Actions tab that takes the recipient's email address as an input and runs scripts/send_report.py --to with that address.
- Timestamp: 20261117T052440Z
- Run: billing subscription, runner routine, location cloud, id 20261117T052356Z-0d5cc2; started 2026-11-17T05:24:40Z, ended 2026-11-17T05:26:21Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.07 to 0.07, from 6 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.56 over 6 call(s); agent $0.42, judge $0.00, guard $0.14; last agent call $0.22
- Harness: Claude Code `2.1.326 (Claude Code)`; models used: with_guidance_full=claude-opus-5-5; with_guidance_full_minus_section=claude-opus-5-5

| Arm | Mode | Pair | Bytes | Guard | Objective | Judge overall | Cost (USD) | Error |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| with_guidance_full | full | in context | 26653 | ok (saw it); receipt ok | 5/6 | 5.7 | 0.2019 |  |
| with_guidance_full_minus_section | full-minus-section | in context | 25456 | ok (saw it); receipt ok | 5/6 | 7.7 | 0.2193 |  |

Judge: when the version with the skill or guidance passes more checks than its partner, the judge isn't needed and both are skipped. On a tie or a loss, the judge scores both from 0 to 10.
