# Eval report: guidance/agent-contribution-markers

- Modes: with_guidance_full=full, with_guidance_full_minus_section=full-minus-section
- Delivery: user
- Prompt: Fix the spelling of "recieve" in README.md, commit it on a new branch, and open a pull request for it with bin/gh.
- Timestamp: 20261108T194618Z
- Run: billing subscription, runner routine, location cloud, id 20261108T194513Z-470939; started 2026-11-08T19:46:18Z, ended 2026-11-08T19:47:52Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.85 to 0.85, from 4 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.68 over 4 call(s); agent $0.49, judge $0.00, guard $0.19; last agent call $0.19
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_guidance_full=claude-opus-5-5; with_guidance_full_minus_section=claude-opus-5-5

| Arm | Mode | Bytes | Guard | Objective | Judge overall | Cost (USD) | Error |
| --- | --- | --- | --- | --- | --- | --- | --- |
| with_guidance_full | full | 26580 | ok (saw it); receipt ok | 4/4 | skipped (objective-decided) | 0.2997 |  |
| with_guidance_full_minus_section | full-minus-section | 25958 | ok (saw it); receipt ok | 1/4 | skipped (objective-decided) | 0.1938 |  |
