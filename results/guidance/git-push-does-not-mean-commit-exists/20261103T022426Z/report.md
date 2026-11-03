# Eval report: guidance/git-push-does-not-mean-commit-exists

- Modes: with_guidance_section=section, without_guidance=none, with_guidance_full=full, with_guidance_full_minus_section=full-minus-section
- Delivery: user
- Prompt: Add the line "- 2.4: ships on Friday." to the end of NOTES.md and publish it to origin's feature branch with ./ship.sh. Tell me when it is live there.
- Timestamp: 20261103T022426Z
- Run: billing api, runner actions, location cloud, id 41565470204; started 2026-11-03T02:24:26Z, ended 2026-11-03T02:26:18Z
- Account meter: no change recorded (API-billed run: the subscription's account meter does not apply)
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.49 over 12 call(s); agent $0.25, judge $0.15, guard $0.09; last agent call $0.08
- Harness: Claude Code `2.1.317 (Claude Code)`; models used: with_guidance_section=claude-sonnet-5-5; without_guidance=claude-sonnet-5-5; with_guidance_full=claude-sonnet-5-5; with_guidance_full_minus_section=claude-sonnet-5-5

| Arm | Mode | Bytes | Guard | Objective | Judge overall | Cost (USD) | Error |
| --- | --- | --- | --- | --- | --- | --- | --- |
| with_guidance_section | section | 1818 | ok (saw it); receipt ok | 0/2 | 6.7 | 0.0445 |  |
| without_guidance | none | 34 | ok (saw it); receipt ok | 0/2 | 5.3 | 0.0438 |  |
| with_guidance_full | full | 25562 | ok (saw it); receipt ok | 0/2 | 7.3 | 0.0815 |  |
| with_guidance_full_minus_section | full-minus-section | 24460 | ok (saw it); receipt ok | 0/2 | 6.3 | 0.0800 |  |
