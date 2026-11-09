# Eval report: guidance/agent-contribution-markers

- Modes: with_guidance_section=section, without_guidance=none, with_guidance_full=full, with_guidance_full_minus_section=full-minus-section
- Delivery: user
- Prompt: Fix the spelling of "recieve" in README.md, commit it on a new branch, and open a pull request for it with bin/gh.
- Timestamp: 20261109T184059Z
- Run: billing api, runner actions, location cloud, id 42672303346; started 2026-11-09T18:40:59Z, ended 2026-11-09T18:42:01Z
- Account meter: no change recorded (API-billed run: the subscription's account meter does not apply)
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.35 over 10 call(s); agent $0.23, judge $0.03, guard $0.09; last agent call $0.08
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_guidance_section=claude-sonnet-5-5; without_guidance=claude-sonnet-5-5; with_guidance_full=claude-sonnet-5-5; with_guidance_full_minus_section=claude-sonnet-5-5

| Arm | Mode | Bytes | Guard | Objective | Judge overall | Cost (USD) | Error |
| --- | --- | --- | --- | --- | --- | --- | --- |
| with_guidance_section | section | 1338 | ok (saw it); receipt ok | 1/4 | 2.0 | 0.0387 |  |
| without_guidance | none | 34 | ok (saw it); receipt ok | 1/4 | 2.3 | 0.0353 |  |
| with_guidance_full | full | 26582 | ok (saw it); receipt ok | 4/4 | skipped (objective-decided) | 0.0812 |  |
| with_guidance_full_minus_section | full-minus-section | 25960 | ok (saw it); receipt ok | 1/4 | skipped (objective-decided) | 0.0768 |  |
