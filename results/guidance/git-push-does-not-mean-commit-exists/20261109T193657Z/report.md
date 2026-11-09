# Eval report: guidance/git-push-does-not-mean-commit-exists

- Modes: with_guidance_section=section, without_guidance=none, with_guidance_full=full, with_guidance_full_minus_section=full-minus-section
- Delivery: user
- Prompt: Add the line "- 2.4: ships on Friday." to the end of NOTES.md and publish it to origin's feature branch with ./ship.sh. Tell me when it is live there.
- Timestamp: 20261109T193657Z
- Run: billing api, runner actions, location cloud, id 42680911395; started 2026-11-09T19:36:57Z, ended 2026-11-09T19:38:11Z
- Account meter: no change recorded (API-billed run: the subscription's account meter does not apply)
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.38 over 12 call(s); agent $0.21, judge $0.08, guard $0.09; last agent call $0.07
- Harness: Claude Code `2.1.321 (Claude Code)`; models used: with_guidance_section=claude-sonnet-5-5; without_guidance=claude-sonnet-5-5; with_guidance_full=claude-sonnet-5-5; with_guidance_full_minus_section=claude-sonnet-5-5

| Arm | Mode | Bytes | Guard | Objective | Judge overall | Cost (USD) | Error |
| --- | --- | --- | --- | --- | --- | --- | --- |
| with_guidance_section | section | 1818 | ok (saw it); receipt ok | 0/2 | 7.3 | 0.0377 |  |
| without_guidance | none | 34 | ok (saw it); receipt ok | 0/2 | 7.0 | 0.0390 |  |
| with_guidance_full | full | 26582 | ok (saw it); receipt ok | 0/2 | 7.0 | 0.0644 |  |
| with_guidance_full_minus_section | full-minus-section | 25480 | ok (saw it); receipt ok | 0/2 | 7.3 | 0.0696 |  |
