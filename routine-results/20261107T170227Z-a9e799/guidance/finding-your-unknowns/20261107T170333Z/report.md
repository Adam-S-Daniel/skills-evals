# Eval report: guidance/finding-your-unknowns

- Modes: with_guidance_full=full, with_guidance_full_minus_section=full-minus-section
- Delivery: user
- Prompt: We keep merging changes to src/ without a CHANGELOG.md entry. Make sure that stops happening.
- Timestamp: 20261107T170333Z
- Run: billing subscription, runner routine, location cloud, id 20261107T170227Z-a9e799; started 2026-11-07T17:03:33Z, ended 2026-11-07T17:06:37Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.57 to 0.57, from 6 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $1.12 over 6 call(s); agent $0.87, judge $0.04, guard $0.22; last agent call $0.47
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_guidance_full=claude-haiku-5-5, claude-opus-5-5; with_guidance_full_minus_section=claude-opus-5-5, claude-sonnet-5-5

| Arm | Mode | Bytes | Guard | Objective | Judge overall | Cost (USD) | Error |
| --- | --- | --- | --- | --- | --- | --- | --- |
| with_guidance_full | full | 26267 | ok (saw it); receipt ok | 1/1 | 9.6 | 0.3972 |  |
| with_guidance_full_minus_section | full-minus-section | 25252 | ok (saw it); receipt ok | 1/1 | 9.7 | 0.4680 |  |
