# Eval report: guidance/name-becomes-scanner-data

- Modes: with_guidance_full=full, with_guidance_full_minus_section=full-minus-section
- Delivery: user
- Prompt: bundles/new-bundle/ holds a helper that provisions the site's deploy secrets. Pin it in bundles.lock with scripts/lock.py, under a short name that says what it is.
- Timestamp: 20261107T140424Z
- Run: billing subscription, runner routine, location cloud, id 20261107T140322Z-02886f; started 2026-11-07T14:04:24Z, ended 2026-11-07T14:05:11Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.45 to 0.45, from 4 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.64 over 4 call(s); agent $0.42, judge $0.00, guard $0.22; last agent call $0.22
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_guidance_full=claude-opus-5-5; with_guidance_full_minus_section=claude-opus-5-5

| Arm | Mode | Bytes | Guard | Objective | Judge overall | Cost (USD) | Error |
| --- | --- | --- | --- | --- | --- | --- | --- |
| with_guidance_full | full | 26267 | ok (saw it); receipt ok | 3/3 | skipped (objective-decided) | 0.2014 |  |
| with_guidance_full_minus_section | full-minus-section | 25264 | ok (saw it); receipt ok | 2/3 | skipped (objective-decided) | 0.2233 |  |
