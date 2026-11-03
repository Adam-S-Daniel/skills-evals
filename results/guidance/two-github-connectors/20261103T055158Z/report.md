# Eval report: guidance/two-github-connectors

- Modes: with_guidance_section=section, without_guidance=none, with_guidance_full=full, with_guidance_full_minus_section=full-minus-section
- Delivery: user
- Prompt: In this session the only GitHub tools are the claude.ai organization connector's (github-mcp). In a few lines: how do I check whether pull request 12's CI passed with it, and what can it not do that I would need another tool for?
- Timestamp: 20261103T055158Z
- Run: billing api, runner actions, location cloud, id 41585078142; started 2026-11-03T05:51:58Z, ended 2026-11-03T05:53:01Z
- Account meter: no change recorded (API-billed run: the subscription's account meter does not apply)
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.62 over 10 call(s); agent $0.38, judge $0.07, guard $0.17; last agent call $0.12
- Harness: Claude Code `2.1.317 (Claude Code)`; models used: with_guidance_section=claude-opus-5-5; without_guidance=claude-opus-5-5; with_guidance_full=claude-opus-5-5; with_guidance_full_minus_section=claude-opus-5-5

| Arm | Mode | Bytes | Guard | Objective | Judge overall | Cost (USD) | Error |
| --- | --- | --- | --- | --- | --- | --- | --- |
| with_guidance_section | section | 1999 | ok (saw it); receipt ok | 2/2 | skipped (objective-decided) | 0.0614 |  |
| without_guidance | none | 34 | ok (saw it); receipt ok | 1/2 | skipped (objective-decided) | 0.0904 |  |
| with_guidance_full | full | 25562 | ok (saw it); receipt ok | 2/2 | 8.7 | 0.1074 |  |
| with_guidance_full_minus_section | full-minus-section | 24279 | ok (saw it); receipt ok | 2/2 | 4.7 | 0.1228 |  |
