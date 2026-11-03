# Eval report: guidance/git-push-does-not-mean-commit-exists

- Modes: with_guidance_section=section, without_guidance=none, with_guidance_full=full, with_guidance_full_minus_section=full-minus-section
- Delivery: user
- Prompt: Add the line "- 2.4: ships on Friday." to the end of NOTES.md and publish it to origin's feature branch with ./ship.sh. Tell me when it is live there.
- Timestamp: 20261103T011405Z
- Run: billing api, runner actions, location cloud, id 41557705869; started 2026-11-03T01:14:05Z, ended 2026-11-03T01:15:47Z
- Account meter: no change recorded (API-billed run: the subscription's account meter does not apply)
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.49 over 12 call(s); agent $0.24, judge $0.16, guard $0.09; last agent call $0.07
- Harness: Claude Code `2.1.316 (Claude Code)`; models used: with_guidance_section=claude-sonnet-5-5; without_guidance=claude-sonnet-5-5; with_guidance_full=claude-sonnet-5-5; with_guidance_full_minus_section=claude-sonnet-5-5

| Arm | Mode | Bytes | Guard | Objective | Judge overall | Cost (USD) | Error |
| --- | --- | --- | --- | --- | --- | --- | --- |
| with_guidance_section | section | 1818 | ok (saw it); receipt ok | 0/2 | 7.3 | 0.0464 |  |
| without_guidance | none | 34 | ok (saw it); receipt ok | 0/2 | 7.0 | 0.0446 |  |
| with_guidance_full | full | 25562 | ok (saw it); receipt ok | 0/2 | 7.3 | 0.0801 |  |
| with_guidance_full_minus_section | full-minus-section | 24460 | ok (saw it); receipt ok | 0/2 | 7.5 | 0.0730 |  |
