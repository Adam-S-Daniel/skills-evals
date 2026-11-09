# Eval report: guidance/turn-lessons-into-checks

- Modes: with_guidance_section=section, without_guidance=none, with_guidance_full=full, with_guidance_full_minus_section=full-minus-section
- Delivery: user
- Prompt: Review note from Dana on my last change: "docs/api.md was hand-edited again. It is generated from src/api.yaml, so the next regeneration wipes the new /refunds text." Move that text into src/api.yaml, regenerate the docs, and commit.
- Timestamp: 20261109T221443Z
- Run: billing api, runner actions, location cloud, id 42707173182; started 2026-11-09T22:14:43Z, ended 2026-11-09T22:16:40Z
- Account meter: no change recorded (API-billed run: the subscription's account meter does not apply)
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.49 over 10 call(s); agent $0.37, judge $0.03, guard $0.09; last agent call $0.10
- Harness: Claude Code `2.1.321 (Claude Code)`; models used: with_guidance_section=claude-sonnet-5-5; without_guidance=claude-sonnet-5-5; with_guidance_full=claude-sonnet-5-5; with_guidance_full_minus_section=claude-sonnet-5-5

| Arm | Mode | Bytes | Guard | Objective | Judge overall | Cost (USD) | Error |
| --- | --- | --- | --- | --- | --- | --- | --- |
| with_guidance_section | section | 1421 | ok (saw it); receipt ok | 3/3 | skipped (objective-decided) | 0.1021 |  |
| without_guidance | none | 34 | ok (saw it); receipt ok | 1/3 | skipped (objective-decided) | 0.0646 |  |
| with_guidance_full | full | 26582 | ok (saw it); receipt ok | 1/3 | 4.0 | 0.1002 |  |
| with_guidance_full_minus_section | full-minus-section | 25877 | ok (saw it); receipt ok | 1/3 | 4.0 | 0.1025 |  |
