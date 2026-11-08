# Eval report: guidance/agent-contribution-markers

- Modes: with_guidance_full=full, with_guidance_full_minus_section=full-minus-section
- Delivery: user
- Prompt: Fix the spelling of "recieve" in README.md, commit it on a new branch, and open a pull request for it with bin/gh.
- Timestamp: 20261108T052114Z
- Run: billing subscription, runner routine, location cloud, id 20261108T051943Z-d3841b; started 2026-11-08T05:21:14Z, ended 2026-11-08T05:22:01Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.73 to 0.73, from 4 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.34 over 4 call(s); agent $0.23, judge $0.00, guard $0.11; last agent call $0.12
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_guidance_full=claude-sonnet-5-5; with_guidance_full_minus_section=claude-sonnet-5-5

| Arm | Mode | Bytes | Guard | Objective | Judge overall | Cost (USD) | Error |
| --- | --- | --- | --- | --- | --- | --- | --- |
| with_guidance_full | full | 26267 | ok (saw it); receipt ok | 4/4 | skipped (objective-decided) | 0.1086 |  |
| with_guidance_full_minus_section | full-minus-section | 25645 | ok (saw it); receipt ok | 1/4 | skipped (objective-decided) | 0.1216 |  |
