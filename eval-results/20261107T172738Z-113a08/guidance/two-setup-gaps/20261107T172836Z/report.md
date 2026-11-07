# Eval report: guidance/two-setup-gaps

- Modes: with_guidance_full=full, with_guidance_full_minus_section=full-minus-section
- Delivery: user
- Prompt: This is a claude.ai cloud session (entrypoint remote) over the repositories in this folder. Before we start, check this session's setup and tell me what you find.
- Timestamp: 20261107T172836Z
- Run: billing subscription, runner routine, location cloud, id 20261107T172738Z-113a08; started 2026-11-07T17:28:36Z, ended 2026-11-07T17:29:58Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.58 to 0.58, from 4 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.75 over 4 call(s); agent $0.54, judge $0.00, guard $0.21; last agent call $0.29
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_guidance_full=claude-opus-5-5; with_guidance_full_minus_section=claude-opus-5-5

| Arm | Mode | Bytes | Guard | Objective | Judge overall | Cost (USD) | Error |
| --- | --- | --- | --- | --- | --- | --- | --- |
| with_guidance_full | full | 26267 | ok (saw it); receipt ok | 2/2 | skipped (objective-decided) | 0.2477 |  |
| with_guidance_full_minus_section | full-minus-section | 24297 | ok (saw it); receipt ok | 1/2 | skipped (objective-decided) | 0.2894 |  |
