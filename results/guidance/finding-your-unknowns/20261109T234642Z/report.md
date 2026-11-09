# Eval report: guidance/finding-your-unknowns

- Modes: with_guidance_section=section, without_guidance=none, with_guidance_full=full, with_guidance_full_minus_section=full-minus-section
- Delivery: user
- Prompt: Add a line to AGENTS.md telling agents that every new file in db/migrations/ needs a matching file with the same name in db/rollbacks/. We keep forgetting the rollback.
- Timestamp: 20261109T234642Z
- Run: billing api, runner actions, location cloud, id 42718601638; started 2026-11-09T23:46:42Z, ended 2026-11-09T23:47:31Z
- Account meter: no change recorded (API-billed run: the subscription's account meter does not apply)
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.32 over 12 call(s); agent $0.18, judge $0.05, guard $0.09; last agent call $0.06
- Harness: Claude Code `2.1.321 (Claude Code)`; models used: with_guidance_section=claude-sonnet-5-5; without_guidance=claude-sonnet-5-5; with_guidance_full=claude-sonnet-5-5; with_guidance_full_minus_section=claude-sonnet-5-5

| Arm | Mode | Bytes | Guard | Objective | Judge overall | Cost (USD) | Error |
| --- | --- | --- | --- | --- | --- | --- | --- |
| with_guidance_section | section | 1731 | ok (saw it); receipt ok | 1/2 | 1.0 | 0.0296 |  |
| without_guidance | none | 34 | ok (saw it); receipt ok | 1/2 | 1.0 | 0.0321 |  |
| with_guidance_full | full | 26582 | ok (saw it); receipt ok | 1/2 | 1.7 | 0.0608 |  |
| with_guidance_full_minus_section | full-minus-section | 25567 | ok (saw it); receipt ok | 1/2 | 1.0 | 0.0604 |  |
