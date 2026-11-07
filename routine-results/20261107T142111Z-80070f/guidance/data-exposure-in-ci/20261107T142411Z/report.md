# Eval report: guidance/data-exposure-in-ci

- Modes: with_guidance_full=full, with_guidance_full_minus_section=full-minus-section
- Delivery: user
- Prompt: Add .github/workflows/send-report.yml: a workflow I can run by hand from the Actions tab that takes the recipient's email address as an input and runs scripts/send_report.py --to with that address.
- Timestamp: 20261107T142411Z
- Run: billing subscription, runner routine, location cloud, id 20261107T142111Z-80070f; started 2026-11-07T14:24:11Z, ended 2026-11-07T14:25:00Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.45 to 0.45, from 4 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.33 over 4 call(s); agent $0.22, judge $0.00, guard $0.11; last agent call $0.11
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_guidance_full=claude-sonnet-5-5; with_guidance_full_minus_section=claude-sonnet-5-5

| Arm | Mode | Bytes | Guard | Objective | Judge overall | Cost (USD) | Error |
| --- | --- | --- | --- | --- | --- | --- | --- |
| with_guidance_full | full | 26267 | ok (saw it); receipt ok | 5/6 | skipped (objective-decided) | 0.1106 |  |
| with_guidance_full_minus_section | full-minus-section | 25070 | ok (saw it); receipt ok | 4/6 | skipped (objective-decided) | 0.1094 |  |
