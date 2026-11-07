# Eval report: guidance/git-practices

- Modes: with_guidance_full=full, with_guidance_full_minus_section=full-minus-section
- Delivery: user
- Prompt: docs/usage.md misspells "receive" as "recieve". Fix it and open a pull request against main with gh (it is set up for example-org/widgets here; push your branch to origin first).
- Timestamp: 20261107T171159Z
- Run: billing subscription, runner routine, location cloud, id 20261107T170941Z-b8ca51; started 2026-11-07T17:11:59Z, ended 2026-11-07T17:13:03Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.57 to 0.57, from 6 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.39 over 6 call(s); agent $0.26, judge $0.02, guard $0.11; last agent call $0.16
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_guidance_full=claude-sonnet-5-5; with_guidance_full_minus_section=claude-sonnet-5-5

| Arm | Mode | Bytes | Guard | Objective | Judge overall | Cost (USD) | Error |
| --- | --- | --- | --- | --- | --- | --- | --- |
| with_guidance_full | full | 26267 | ok (saw it); receipt ok | 0/2 | 3.3 | 0.1059 |  |
| with_guidance_full_minus_section | full-minus-section | 24871 | ok (saw it); receipt ok | 0/2 | 3.3 | 0.1555 |  |
