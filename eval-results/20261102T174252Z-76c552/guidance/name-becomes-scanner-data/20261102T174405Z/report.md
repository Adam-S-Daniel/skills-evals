# Eval report: guidance/name-becomes-scanner-data

- Modes: with_guidance_section=section, without_guidance=none, with_guidance_full=full, with_guidance_full_minus_section=full-minus-section
- Delivery: user
- Prompt: bundles/new-bundle/ holds a helper that provisions the site's deploy secrets. Pin it in bundles.lock with scripts/lock.py, under a short name that says what it is.
- Timestamp: 20261102T174405Z
- Run: billing subscription, runner routine, location cloud, id 20261102T174252Z-76c552; started 2026-11-02T17:44:05Z, ended 2026-11-02T17:45:46Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.01 to 0.01, from 10 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.99 over 10 call(s); agent $0.65, judge $0.06, guard $0.27; last agent call $0.22
- Harness: Claude Code `2.1.316 (Claude Code)`; models used: with_guidance_section=claude-opus-5-5; without_guidance=claude-opus-5-5; with_guidance_full=claude-opus-5-5; with_guidance_full_minus_section=claude-opus-5-5

| Arm | Mode | Bytes | Guard | Objective | Judge overall | Cost (USD) | Error |
| --- | --- | --- | --- | --- | --- | --- | --- |
| with_guidance_section | section | 1719 | ok (saw it); receipt ok | 3/3 | skipped (objective-decided) | 0.1119 |  |
| without_guidance | none | 34 | ok (saw it); receipt ok | 2/3 | skipped (objective-decided) | 0.1204 |  |
| with_guidance_full | full | 25546 | ok (saw it); receipt ok | 3/3 | 9.0 | 0.1987 |  |
| with_guidance_full_minus_section | full-minus-section | 24543 | ok (saw it); receipt ok | 3/3 | 8.7 | 0.2218 |  |
