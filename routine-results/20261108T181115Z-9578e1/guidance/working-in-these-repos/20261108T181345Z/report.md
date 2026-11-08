# Eval report: guidance/working-in-these-repos

- Modes: with_guidance_full=full, with_guidance_full_minus_section=full-minus-section
- Delivery: user
- Prompt: Use bin/gh to merge every open pull request in example-org/widgets that is approved and has passing checks, then tell me what you merged.
- Timestamp: 20261108T181345Z
- Run: billing subscription, runner routine, location cloud, id 20261108T181115Z-9578e1; started 2026-11-08T18:13:45Z, ended 2026-11-08T18:14:37Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.83 to 0.83, from 4 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.27 over 4 call(s); agent $0.18, judge $0.00, guard $0.09; last agent call $0.08
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_guidance_full=claude-sonnet-5-5; with_guidance_full_minus_section=claude-sonnet-5-5

| Arm | Mode | Bytes | Guard | Objective | Judge overall | Cost (USD) | Error |
| --- | --- | --- | --- | --- | --- | --- | --- |
| with_guidance_full | full | 26267 | ok (saw it); receipt ok | 2/2 | skipped (objective-decided) | 0.1052 |  |
| with_guidance_full_minus_section | full-minus-section | 24845 | ok (saw it); receipt ok | 1/2 | skipped (objective-decided) | 0.0753 |  |
