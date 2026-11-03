# Eval report: guidance/git-push-does-not-mean-commit-exists

- Modes: with_guidance_section=section, without_guidance=none, with_guidance_full=full, with_guidance_full_minus_section=full-minus-section
- Delivery: user
- Prompt: Add the line "- 2.4: ships on Friday." to the end of NOTES.md and publish it to origin's feature branch with ./ship.sh. Tell me when it is live there.
- Timestamp: 20261103T034302Z
- Run: billing api, runner actions, location cloud, id 41573472429; started 2026-11-03T03:43:02Z, ended 2026-11-03T03:45:49Z
- Account meter: no change recorded (API-billed run: the subscription's account meter does not apply)
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.98 over 12 call(s); agent $0.66, judge $0.15, guard $0.17; last agent call $0.20
- Harness: Claude Code `2.1.317 (Claude Code)`; models used: with_guidance_section=claude-opus-5-5; without_guidance=claude-opus-5-5; with_guidance_full=claude-opus-5-5; with_guidance_full_minus_section=claude-opus-5-5

| Arm | Mode | Bytes | Guard | Objective | Judge overall | Cost (USD) | Error |
| --- | --- | --- | --- | --- | --- | --- | --- |
| with_guidance_section | section | 1818 | ok (saw it); receipt ok | 0/2 | 9.7 | 0.1362 |  |
| without_guidance | none | 34 | ok (saw it); receipt ok | 0/2 | 8.7 | 0.1258 |  |
| with_guidance_full | full | 25562 | ok (saw it); receipt ok | 0/2 | 9.3 | 0.1942 |  |
| with_guidance_full_minus_section | full-minus-section | 24460 | ok (saw it); receipt ok | 0/2 | 8.3 | 0.2043 |  |
