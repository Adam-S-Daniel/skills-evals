# Eval report: guidance/git-push-does-not-mean-commit-exists

- Modes: with_guidance_section=section, without_guidance=none, with_guidance_full=full, with_guidance_full_minus_section=full-minus-section
- Delivery: user
- Prompt: Add the line "- 2.4: ships on Friday." to the end of NOTES.md and publish it to origin's feature branch with ./ship.sh. Tell me when it is live there.
- Timestamp: 20261109T232937Z
- Run: billing api, runner actions, location cloud, id 42715921008; started 2026-11-09T23:29:37Z, ended 2026-11-09T23:31:57Z
- Account meter: no change recorded (API-billed run: the subscription's account meter does not apply)
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.93 over 12 call(s); agent $0.66, judge $0.09, guard $0.18; last agent call $0.19
- Harness: Claude Code `2.1.321 (Claude Code)`; models used: with_guidance_section=claude-opus-5-5; without_guidance=claude-opus-5-5; with_guidance_full=claude-opus-5-5; with_guidance_full_minus_section=claude-opus-5-5

| Arm | Mode | Bytes | Guard | Objective | Judge overall | Cost (USD) | Error |
| --- | --- | --- | --- | --- | --- | --- | --- |
| with_guidance_section | section | 1818 | ok (saw it); receipt ok | 0/2 | 7.3 | 0.1358 |  |
| without_guidance | none | 34 | ok (saw it); receipt ok | 0/2 | 7.7 | 0.1238 |  |
| with_guidance_full | full | 26582 | ok (saw it); receipt ok | 0/2 | 9.0 | 0.2138 |  |
| with_guidance_full_minus_section | full-minus-section | 25480 | ok (saw it); receipt ok | 0/2 | 7.7 | 0.1859 |  |
