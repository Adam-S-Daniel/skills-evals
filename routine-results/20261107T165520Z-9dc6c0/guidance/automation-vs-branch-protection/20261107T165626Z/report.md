# Eval report: guidance/automation-vs-branch-protection

- Modes: with_guidance_full=full, with_guidance_full_minus_section=full-minus-section
- Delivery: user
- Prompt: docs/stats.json keeps going stale because people forget to run scripts/gen_stats.py. Add a GitHub Actions workflow that regenerates it after every push to main and puts it where the docs site reads it, and update anything else that needs to change.
- Timestamp: 20261107T165626Z
- Run: billing subscription, runner routine, location cloud, id 20261107T165520Z-9dc6c0; started 2026-11-07T16:56:26Z, ended 2026-11-07T17:00:40Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.56 to 0.57, from 5 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $1.40 over 4 call(s); agent $1.19, judge $0.00, guard $0.21; last agent call $0.44
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_guidance_full=claude-opus-5-5, claude-sonnet-5-5; with_guidance_full_minus_section=claude-haiku-5-5, claude-opus-5-5

| Arm | Mode | Bytes | Guard | Objective | Judge overall | Cost (USD) | Error |
| --- | --- | --- | --- | --- | --- | --- | --- |
| with_guidance_full | full | 26267 | ok (saw it); receipt ok | 5/5 | skipped (objective-decided) | 0.7493 |  |
| with_guidance_full_minus_section | full-minus-section | 24066 | ok (saw it); receipt ok | 4/5 | skipped (objective-decided) | 0.4380 |  |
