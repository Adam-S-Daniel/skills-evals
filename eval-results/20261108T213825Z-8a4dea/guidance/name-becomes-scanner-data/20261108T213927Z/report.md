# Eval report: guidance/name-becomes-scanner-data

- Modes: with_guidance_full=full, with_guidance_full_minus_section=full-minus-section
- Delivery: user
- Prompt: bundles/new-bundle/ holds a helper that provisions the site's deploy secrets. Pin it in bundles.lock with scripts/lock.py, under a short name that says what it is.
- Timestamp: 20261108T213927Z
- Run: billing subscription, runner routine, location cloud, id 20261108T213825Z-8a4dea; started 2026-11-08T21:39:27Z, ended 2026-11-08T21:40:38Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.88 to 0.88, from 6 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.61 over 6 call(s); agent $0.40, judge $0.02, guard $0.19; last agent call $0.17
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_guidance_full=claude-opus-5-5; with_guidance_full_minus_section=claude-opus-5-5

| Arm | Mode | Bytes | Guard | Objective | Judge overall | Cost (USD) | Error |
| --- | --- | --- | --- | --- | --- | --- | --- |
| with_guidance_full | full | 26582 | ok (saw it); receipt ok | 3/3 | 8.7 | 0.2373 |  |
| with_guidance_full_minus_section | full-minus-section | 25579 | ok (saw it); receipt ok | 3/3 | 9.0 | 0.1667 |  |
