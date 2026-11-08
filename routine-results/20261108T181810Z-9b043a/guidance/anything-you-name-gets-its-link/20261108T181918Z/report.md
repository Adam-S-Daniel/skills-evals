# Eval report: guidance/anything-you-name-gets-its-link

- Modes: with_guidance_full=full, with_guidance_full_minus_section=full-minus-section
- Delivery: user
- Prompt: Write DONE.md, a short summary of what landed this week, from STATUS.json.
- Timestamp: 20261108T181918Z
- Run: billing subscription, runner routine, location cloud, id 20261108T181810Z-9b043a; started 2026-11-08T18:19:18Z, ended 2026-11-08T18:19:42Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.83 to 0.83, from 4 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.20 over 4 call(s); agent $0.13, judge $0.00, guard $0.07; last agent call $0.06
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_guidance_full=claude-sonnet-5-5; with_guidance_full_minus_section=claude-sonnet-5-5

| Arm | Mode | Bytes | Guard | Objective | Judge overall | Cost (USD) | Error |
| --- | --- | --- | --- | --- | --- | --- | --- |
| with_guidance_full | full | 26267 | ok (saw it); receipt ok | 3/3 | skipped (objective-decided) | 0.0641 |  |
| with_guidance_full_minus_section | full-minus-section | 25381 | ok (saw it); receipt ok | 0/3 | skipped (objective-decided) | 0.0625 |  |
