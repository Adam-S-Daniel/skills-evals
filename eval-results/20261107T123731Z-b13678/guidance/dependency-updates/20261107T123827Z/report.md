# Eval report: guidance/dependency-updates

- Modes: with_guidance_full=full, with_guidance_full_minus_section=full-minus-section
- Delivery: user
- Prompt: Add a Dependabot config that keeps this repository's npm packages and its GitHub Actions up to date, checking weekly.
- Timestamp: 20261107T123827Z
- Run: billing subscription, runner routine, location cloud, id 20261107T123731Z-b13678; started 2026-11-07T12:38:27Z, ended 2026-11-07T12:38:53Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.43 to 0.43, from 4 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.30 over 4 call(s); agent $0.19, judge $0.00, guard $0.11; last agent call $0.10
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_guidance_full=claude-sonnet-5-5; with_guidance_full_minus_section=claude-sonnet-5-5

| Arm | Mode | Bytes | Guard | Objective | Judge overall | Cost (USD) | Error |
| --- | --- | --- | --- | --- | --- | --- | --- |
| with_guidance_full | full | 26267 | ok (saw it); receipt ok | 4/4 | skipped (objective-decided) | 0.0954 |  |
| with_guidance_full_minus_section | full-minus-section | 25733 | ok (saw it); receipt ok | 3/4 | skipped (objective-decided) | 0.0983 |  |
