# Eval report: guidance/dependency-updates

- Modes: with_guidance_section=section, without_guidance=none, with_guidance_full=full, with_guidance_full_minus_section=full-minus-section
- Delivery: user
- Prompt: Add a Dependabot config that keeps this repository's npm packages and its GitHub Actions up to date, checking weekly.
- Timestamp: 20261103T181831Z
- Run: billing subscription, runner routine, location cloud, id 20261103T180650Z-233896; started 2026-11-03T18:18:31Z, ended 2026-11-03T18:20:22Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.64 to 0.64, from 8 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $1.01 over 8 call(s); agent $0.74, judge $0.00, guard $0.27; last agent call $0.26
- Harness: Claude Code `2.1.317 (Claude Code)`; models used: with_guidance_section=claude-opus-5-5; without_guidance=claude-opus-5-5; with_guidance_full=claude-opus-5-5; with_guidance_full_minus_section=claude-haiku-5-5, claude-opus-5-5

| Arm | Mode | Bytes | Guard | Objective | Judge overall | Cost (USD) | Error |
| --- | --- | --- | --- | --- | --- | --- | --- |
| with_guidance_section | section | 1250 | ok (saw it); receipt ok | 4/4 | skipped (objective-decided) | 0.1271 |  |
| without_guidance | none | 34 | ok (saw it); receipt ok | 2/4 | skipped (objective-decided) | 0.1164 |  |
| with_guidance_full | full | 25562 | ok (saw it); receipt ok | 4/4 | skipped (objective-decided) | 0.2306 |  |
| with_guidance_full_minus_section | full-minus-section | 25028 | ok (saw it); receipt ok | 3/4 | skipped (objective-decided) | 0.2627 |  |
