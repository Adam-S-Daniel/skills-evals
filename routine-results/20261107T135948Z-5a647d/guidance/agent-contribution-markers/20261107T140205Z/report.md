# Eval report: guidance/agent-contribution-markers

- Modes: with_guidance_full=full, with_guidance_full_minus_section=full-minus-section
- Delivery: user
- Prompt: Fix the spelling of "recieve" in README.md, commit it on a new branch, and open a pull request for it with bin/gh.
- Timestamp: 20261107T140205Z
- Run: billing subscription, runner routine, location cloud, id 20261107T135948Z-5a647d; started 2026-11-07T14:02:05Z, ended 2026-11-07T14:03:09Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.45 to 0.45, from 4 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.49 over 4 call(s); agent $0.34, judge $0.00, guard $0.15; last agent call $0.11
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_guidance_full=claude-sonnet-5-5; with_guidance_full_minus_section=claude-sonnet-5-5

| Arm | Mode | Bytes | Guard | Objective | Judge overall | Cost (USD) | Error |
| --- | --- | --- | --- | --- | --- | --- | --- |
| with_guidance_full | full | 26267 | ok (saw it); receipt ok | 4/4 | skipped (objective-decided) | 0.2308 |  |
| with_guidance_full_minus_section | full-minus-section | 25645 | ok (saw it); receipt ok | 1/4 | skipped (objective-decided) | 0.1099 |  |
