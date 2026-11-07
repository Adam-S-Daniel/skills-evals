# Eval report: guidance/fleet-spans-two-owners

- Modes: with_guidance_full=full, with_guidance_full_minus_section=full-minus-section
- Delivery: user
- Prompt: Which repositories in the fleet have no skills.lock at their root? Write them to MISSING.md, one owner/name per line and nothing else, and tell me how you checked.
- Timestamp: 20261107T170803Z
- Run: billing subscription, runner routine, location cloud, id 20261107T170605Z-51f519; started 2026-11-07T17:08:03Z, ended 2026-11-07T17:09:30Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.57 to 0.57, from 6 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.38 over 6 call(s); agent $0.25, judge $0.02, guard $0.11; last agent call $0.12
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_guidance_full=claude-sonnet-5-5; with_guidance_full_minus_section=claude-sonnet-5-5

| Arm | Mode | Bytes | Guard | Objective | Judge overall | Cost (USD) | Error |
| --- | --- | --- | --- | --- | --- | --- | --- |
| with_guidance_full | full | 26267 | ok (saw it); receipt ok | 2/3 | 8.7 | 0.1286 |  |
| with_guidance_full_minus_section | full-minus-section | 25304 | ok (saw it); receipt ok | 3/3 | 10.0 | 0.1221 |  |
