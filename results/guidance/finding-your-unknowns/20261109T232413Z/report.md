# Eval report: guidance/finding-your-unknowns

- Modes: with_guidance_section=section, without_guidance=none, with_guidance_full=full, with_guidance_full_minus_section=full-minus-section
- Delivery: user
- Prompt: Add a line to AGENTS.md telling agents that every new file in db/migrations/ needs a matching file with the same name in db/rollbacks/. We keep forgetting the rollback.
- Timestamp: 20261109T232413Z
- Run: billing api, runner actions, location cloud, id 42715921008; started 2026-11-09T23:24:13Z, ended 2026-11-09T23:26:30Z
- Account meter: no change recorded (API-billed run: the subscription's account meter does not apply)
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.94 over 10 call(s); agent $0.72, judge $0.04, guard $0.18; last agent call $0.28
- Harness: Claude Code `2.1.321 (Claude Code)`; models used: with_guidance_section=claude-opus-5-5; without_guidance=claude-opus-5-5; with_guidance_full=claude-opus-5-5; with_guidance_full_minus_section=claude-opus-5-5

| Arm | Mode | Bytes | Guard | Objective | Judge overall | Cost (USD) | Error |
| --- | --- | --- | --- | --- | --- | --- | --- |
| with_guidance_section | section | 1731 | ok (saw it); receipt ok | 2/2 | skipped (objective-decided) | 0.1196 |  |
| without_guidance | none | 34 | ok (saw it); receipt ok | 1/2 | skipped (objective-decided) | 0.0668 |  |
| with_guidance_full | full | 26582 | ok (saw it); receipt ok | 2/2 | 8.7 | 0.2504 |  |
| with_guidance_full_minus_section | full-minus-section | 25567 | ok (saw it); receipt ok | 2/2 | 9.0 | 0.2803 |  |
