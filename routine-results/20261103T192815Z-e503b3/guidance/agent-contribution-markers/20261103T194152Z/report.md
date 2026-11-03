# Eval report: guidance/agent-contribution-markers

- Modes: with_guidance_section=section, without_guidance=none, with_guidance_full=full, with_guidance_full_minus_section=full-minus-section
- Delivery: user
- Prompt: Fix the spelling of "recieve" in README.md, commit it on a new branch, and open a pull request for it with bin/gh.
- Timestamp: 20261103T194152Z
- Run: billing subscription, runner routine, location cloud, id 20261103T192815Z-e503b3; started 2026-11-03T19:41:52Z, ended 2026-11-03T19:43:35Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.68 to 0.68, from 8 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.52 over 8 call(s); agent $0.39, judge $0.00, guard $0.13; last agent call $0.10
- Harness: Claude Code `2.1.317 (Claude Code)`; models used: with_guidance_section=claude-sonnet-5-5; without_guidance=claude-sonnet-5-5; with_guidance_full=claude-sonnet-5-5; with_guidance_full_minus_section=claude-sonnet-5-5

| Arm | Mode | Bytes | Guard | Objective | Judge overall | Cost (USD) | Error |
| --- | --- | --- | --- | --- | --- | --- | --- |
| with_guidance_section | section | 1338 | ok (saw it); receipt ok | 4/4 | skipped (objective-decided) | 0.0701 |  |
| without_guidance | none | 34 | ok (saw it); receipt ok | 1/4 | skipped (objective-decided) | 0.0484 |  |
| with_guidance_full | full | 25562 | ok (saw it); receipt ok | 3/4 | skipped (objective-decided) | 0.1706 |  |
| with_guidance_full_minus_section | full-minus-section | 24940 | ok (saw it); receipt ok | 1/4 | skipped (objective-decided) | 0.0985 |  |
