# Eval report: guidance/github-404-means-not-authorized

- Modes: with_guidance_full=full, with_guidance_full_minus_section=full-minus-section
- Delivery: user
- Prompt: Someone said PR 17 in example-org/infra was deleted. Use bin/gh to find out what happened to it and write the answer to STATUS.md.
- Timestamp: 20261107T171758Z
- Run: billing subscription, runner routine, location cloud, id 20261107T171652Z-a18950; started 2026-11-07T17:17:58Z, ended 2026-11-07T17:19:15Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.57 to 0.57, from 6 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.74 over 6 call(s); agent $0.49, judge $0.03, guard $0.22; last agent call $0.26
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_guidance_full=claude-opus-5-5; with_guidance_full_minus_section=claude-opus-5-5

| Arm | Mode | Bytes | Guard | Objective | Judge overall | Cost (USD) | Error |
| --- | --- | --- | --- | --- | --- | --- | --- |
| with_guidance_full | full | 26267 | ok (saw it); receipt ok | 2/2 | 8.7 | 0.2307 |  |
| with_guidance_full_minus_section | full-minus-section | 25392 | ok (saw it); receipt ok | 2/2 | 9.0 | 0.2622 |  |
