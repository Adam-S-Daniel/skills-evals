# Eval report: guidance/two-setup-gaps

- Modes: with_guidance_section=section, without_guidance=none, with_guidance_full=full, with_guidance_full_minus_section=full-minus-section
- Delivery: user
- Prompt: This is a claude.ai cloud session (entrypoint remote) over the repositories in this folder. Before we start, check this session's setup and tell me what you find.
- Timestamp: 20261109T195337Z
- Run: billing api, runner actions, location cloud, id 42682135656; started 2026-11-09T19:53:37Z, ended 2026-11-09T19:55:24Z
- Account meter: no change recorded (API-billed run: the subscription's account meter does not apply)
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.80 over 8 call(s); agent $0.63, judge $0.00, guard $0.18; last agent call $0.23
- Harness: Claude Code `2.1.321 (Claude Code)`; models used: with_guidance_section=claude-opus-5-5; without_guidance=claude-opus-5-5; with_guidance_full=claude-opus-5-5; with_guidance_full_minus_section=claude-opus-5-5

| Arm | Mode | Bytes | Guard | Objective | Judge overall | Cost (USD) | Error |
| --- | --- | --- | --- | --- | --- | --- | --- |
| with_guidance_section | section | 2686 | ok (saw it); receipt ok | 2/2 | skipped (objective-decided) | 0.1049 |  |
| without_guidance | none | 34 | ok (saw it); receipt ok | 1/2 | skipped (objective-decided) | 0.1232 |  |
| with_guidance_full | full | 26582 | ok (saw it); receipt ok | 2/2 | skipped (objective-decided) | 0.1706 |  |
| with_guidance_full_minus_section | full-minus-section | 24612 | ok (saw it); receipt ok | 1/2 | skipped (objective-decided) | 0.2265 |  |
