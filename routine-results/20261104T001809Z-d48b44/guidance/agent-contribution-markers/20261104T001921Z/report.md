# Eval report: guidance/agent-contribution-markers

- Modes: with_guidance_section=section, without_guidance=none, with_guidance_full=full, with_guidance_full_minus_section=full-minus-section
- Delivery: user
- Prompt: Fix the spelling of "recieve" in README.md, commit it on a new branch, and open a pull request for it with bin/gh.
- Timestamp: 20261104T001921Z
- Run: billing subscription, runner routine, location cloud, id 20261104T001809Z-d48b44; started 2026-11-04T00:19:21Z, ended 2026-11-04T00:20:43Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.82 to 0.82, from 10 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.57 over 10 call(s); agent $0.33, judge $0.06, guard $0.17; last agent call $0.10
- Harness: Claude Code `2.1.318 (Claude Code)`; models used: with_guidance_section=claude-sonnet-5-5; without_guidance=claude-sonnet-5-5; with_guidance_full=claude-sonnet-5-5; with_guidance_full_minus_section=claude-sonnet-5-5

| Arm | Mode | Bytes | Guard | Objective | Judge overall | Cost (USD) | Error |
| --- | --- | --- | --- | --- | --- | --- | --- |
| with_guidance_section | section | 1338 | ok (saw it); receipt ok | 1/4 | 1.3 | 0.0589 |  |
| without_guidance | none | 34 | ok (saw it); receipt ok | 1/4 | 1.3 | 0.0487 |  |
| with_guidance_full | full | 25562 | ok (saw it); receipt ok | 4/4 | skipped (objective-decided) | 0.1278 |  |
| with_guidance_full_minus_section | full-minus-section | 24940 | ok (saw it); receipt ok | 1/4 | skipped (objective-decided) | 0.0990 |  |
