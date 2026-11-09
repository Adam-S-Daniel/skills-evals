# Eval report: guidance/automation-vs-branch-protection

- Modes: with_guidance_section=section, without_guidance=none, with_guidance_full=full, with_guidance_full_minus_section=full-minus-section
- Delivery: user
- Prompt: The repo has collected dozens of old branches from merged and abandoned pull requests. Add a GitHub Actions workflow that runs weekly and deletes the remote branches that no longer have an open pull request, and update anything else that needs to change.
- Timestamp: 20261109T234330Z
- Run: billing api, runner actions, location cloud, id 42718601638; started 2026-11-09T23:43:30Z, ended 2026-11-09T23:45:47Z
- Account meter: no change recorded (API-billed run: the subscription's account meter does not apply)
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.54 over 10 call(s); agent $0.38, judge $0.07, guard $0.09; last agent call $0.11
- Harness: Claude Code `2.1.321 (Claude Code)`; models used: with_guidance_section=claude-sonnet-5-5; without_guidance=claude-sonnet-5-5; with_guidance_full=claude-sonnet-5-5; with_guidance_full_minus_section=claude-sonnet-5-5

| Arm | Mode | Bytes | Guard | Objective | Judge overall | Cost (USD) | Error |
| --- | --- | --- | --- | --- | --- | --- | --- |
| with_guidance_section | section | 2917 | ok (saw it); receipt ok | 3/5 | 8.3 | 0.0745 |  |
| without_guidance | none | 34 | ok (saw it); receipt ok | 5/5 | 8.3 | 0.0645 |  |
| with_guidance_full | full | 26582 | ok (saw it); receipt ok | 4/5 | skipped (objective-decided) | 0.1340 |  |
| with_guidance_full_minus_section | full-minus-section | 24381 | ok (saw it); receipt ok | 3/5 | skipped (objective-decided) | 0.1087 |  |
