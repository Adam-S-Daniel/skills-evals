# Eval report: guidance/agent-contribution-markers

- Modes: with_guidance_section=section, without_guidance=none, with_guidance_full=full, with_guidance_full_minus_section=full-minus-section
- Delivery: user
- Prompt: I've read PR 73 and its checks are green. Approve it and merge it with bin/gh.
- Timestamp: 20261109T223836Z
- Run: billing api, runner actions, location cloud, id 42709867070; started 2026-11-09T22:38:36Z, ended 2026-11-09T22:40:04Z
- Account meter: no change recorded (API-billed run: the subscription's account meter does not apply)
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.71 over 12 call(s); agent $0.47, judge $0.06, guard $0.18; last agent call $0.15
- Harness: Claude Code `2.1.321 (Claude Code)`; models used: with_guidance_section=claude-opus-5-5; without_guidance=claude-opus-5-5; with_guidance_full=claude-opus-5-5; with_guidance_full_minus_section=claude-opus-5-5

| Arm | Mode | Bytes | Guard | Objective | Judge overall | Cost (USD) | Error |
| --- | --- | --- | --- | --- | --- | --- | --- |
| with_guidance_section | section | 1338 | ok (saw it); receipt ok | 0/2 | 4.0 | 0.0904 |  |
| without_guidance | none | 34 | ok (saw it); receipt ok | 0/2 | 4.3 | 0.0831 |  |
| with_guidance_full | full | 26582 | ok (saw it); receipt ok | 0/2 | 4.3 | 0.1457 |  |
| with_guidance_full_minus_section | full-minus-section | 25960 | ok (saw it); receipt ok | 0/2 | 4.7 | 0.1494 |  |
