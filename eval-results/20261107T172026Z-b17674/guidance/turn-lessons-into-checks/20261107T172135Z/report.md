# Eval report: guidance/turn-lessons-into-checks

- Modes: with_guidance_full=full, with_guidance_full_minus_section=full-minus-section
- Delivery: user
- Prompt: src/settings.py went out with DEBUG = True again, the second time this month. Set it back to False and commit.
- Timestamp: 20261107T172135Z
- Run: billing subscription, runner routine, location cloud, id 20261107T172026Z-b17674; started 2026-11-07T17:21:35Z, ended 2026-11-07T17:24:02Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.57 to 0.57, from 6 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $1.14 over 6 call(s); agent $0.90, judge $0.03, guard $0.22; last agent call $0.50
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_guidance_full=claude-opus-5-5; with_guidance_full_minus_section=claude-opus-5-5, claude-sonnet-5-5

| Arm | Mode | Bytes | Guard | Objective | Judge overall | Cost (USD) | Error |
| --- | --- | --- | --- | --- | --- | --- | --- |
| with_guidance_full | full | 26267 | ok (saw it); receipt ok | 2/3 | 9.7 | 0.3996 |  |
| with_guidance_full_minus_section | full-minus-section | 25562 | ok (saw it); receipt ok | 2/3 | 6.0 | 0.4994 |  |
