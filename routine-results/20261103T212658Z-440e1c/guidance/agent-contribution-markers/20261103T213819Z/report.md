# Eval report: guidance/agent-contribution-markers

- Modes: with_guidance_section=section, without_guidance=none, with_guidance_full=full, with_guidance_full_minus_section=full-minus-section
- Delivery: user
- Prompt: Fix the spelling of "recieve" in README.md, commit it on a new branch, and open a pull request for it with bin/gh.
- Timestamp: 20261103T213819Z
- Run: billing subscription, runner routine, location cloud, id 20261103T212658Z-440e1c; started 2026-11-03T21:38:19Z, ended 2026-11-03T21:40:08Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.73 to 0.74, from 11 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.55 over 10 call(s); agent $0.32, judge $0.06, guard $0.17; last agent call $0.11
- Harness: Claude Code `2.1.317 (Claude Code)`; models used: with_guidance_section=claude-sonnet-5-5; without_guidance=claude-sonnet-5-5; with_guidance_full=claude-sonnet-5-5; with_guidance_full_minus_section=claude-sonnet-5-5

| Arm | Mode | Bytes | Guard | Objective | Judge overall | Cost (USD) | Error |
| --- | --- | --- | --- | --- | --- | --- | --- |
| with_guidance_section | section | 1338 | ok (saw it); receipt ok | 1/4 | 3.0 | 0.0574 |  |
| without_guidance | none | 34 | ok (saw it); receipt ok | 1/4 | 1.3 | 0.0480 |  |
| with_guidance_full | full | 25562 | ok (saw it); receipt ok | 4/4 | skipped (objective-decided) | 0.1072 |  |
| with_guidance_full_minus_section | full-minus-section | 24940 | ok (saw it); receipt ok | 1/4 | skipped (objective-decided) | 0.1101 |  |
