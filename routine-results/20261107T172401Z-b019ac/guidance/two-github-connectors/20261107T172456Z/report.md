# Eval report: guidance/two-github-connectors

- Modes: with_guidance_full=full, with_guidance_full_minus_section=full-minus-section
- Delivery: user
- Prompt: In this session the only GitHub tools are the claude.ai organization connector's (github-mcp). In a few lines: how do I check whether pull request 12's CI passed with it, and what can it not do that I would need another tool for?
- Timestamp: 20261107T172456Z
- Run: billing subscription, runner routine, location cloud, id 20261107T172401Z-b019ac; started 2026-11-07T17:24:56Z, ended 2026-11-07T17:25:34Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.58 to 0.58, from 6 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.58 over 6 call(s); agent $0.34, judge $0.02, guard $0.21; last agent call $0.18
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_guidance_full=claude-opus-5-5; with_guidance_full_minus_section=claude-opus-5-5

| Arm | Mode | Bytes | Guard | Objective | Judge overall | Cost (USD) | Error |
| --- | --- | --- | --- | --- | --- | --- | --- |
| with_guidance_full | full | 26267 | ok (saw it); receipt ok | 2/2 | 7.0 | 0.1677 |  |
| with_guidance_full_minus_section | full-minus-section | 24984 | ok (saw it); receipt ok | 2/2 | 4.7 | 0.1767 |  |
