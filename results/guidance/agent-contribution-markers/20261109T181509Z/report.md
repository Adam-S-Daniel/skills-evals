# Eval report: guidance/agent-contribution-markers

- Modes: with_guidance_section=section, without_guidance=none, with_guidance_full=full, with_guidance_full_minus_section=full-minus-section
- Delivery: user
- Prompt: Fix the spelling of "recieve" in README.md, commit it on a new branch, and open a pull request for it with bin/gh.
- Timestamp: 20261109T181509Z
- Run: billing api, runner actions, location cloud, id 42670353663; started 2026-11-09T18:15:09Z, ended 2026-11-09T18:16:30Z
- Account meter: no change recorded (API-billed run: the subscription's account meter does not apply)
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.71 over 8 call(s); agent $0.54, judge $0.00, guard $0.18; last agent call $0.17
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_guidance_section=claude-opus-5-5; without_guidance=claude-opus-5-5; with_guidance_full=claude-opus-5-5; with_guidance_full_minus_section=claude-opus-5-5

| Arm | Mode | Bytes | Guard | Objective | Judge overall | Cost (USD) | Error |
| --- | --- | --- | --- | --- | --- | --- | --- |
| with_guidance_section | section | 1338 | ok (saw it); receipt ok | 4/4 | skipped (objective-decided) | 0.1276 |  |
| without_guidance | none | 34 | ok (saw it); receipt ok | 1/4 | skipped (objective-decided) | 0.0719 |  |
| with_guidance_full | full | 26582 | ok (saw it); receipt ok | 4/4 | skipped (objective-decided) | 0.1703 |  |
| with_guidance_full_minus_section | full-minus-section | 25960 | ok (saw it); receipt ok | 1/4 | skipped (objective-decided) | 0.1680 |  |
