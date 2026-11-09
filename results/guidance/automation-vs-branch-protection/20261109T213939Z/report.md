# Eval report: guidance/automation-vs-branch-protection

- Modes: with_guidance_section=section, without_guidance=none, with_guidance_full=full, with_guidance_full_minus_section=full-minus-section
- Delivery: user
- Prompt: The repo has collected dozens of old branches from merged and abandoned pull requests. Add a GitHub Actions workflow that runs weekly and deletes the remote branches that no longer have an open pull request, and update anything else that needs to change.
- Timestamp: 20261109T213939Z
- Run: billing api, runner actions, location cloud, id 42699607181; started 2026-11-09T21:39:39Z, ended 2026-11-09T21:41:56Z
- Account meter: no change recorded (API-billed run: the subscription's account meter does not apply)
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.56 over 12 call(s); agent $0.35, judge $0.12, guard $0.09; last agent call $0.09
- Harness: Claude Code `2.1.321 (Claude Code)`; models used: with_guidance_section=claude-sonnet-5-5; without_guidance=claude-sonnet-5-5; with_guidance_full=claude-sonnet-5-5; with_guidance_full_minus_section=claude-sonnet-5-5

| Arm | Mode | Bytes | Guard | Objective | Judge overall | Cost (USD) | Error |
| --- | --- | --- | --- | --- | --- | --- | --- |
| with_guidance_section | section | 2917 | ok (saw it); receipt ok | 3/5 | 9.0 | 0.0773 |  |
| without_guidance | none | 34 | ok (saw it); receipt ok | 5/5 | 8.0 | 0.0603 |  |
| with_guidance_full | full | 26582 | ok (saw it); receipt ok | 3/5 | 8.0 | 0.1180 |  |
| with_guidance_full_minus_section | full-minus-section | 24381 | ok (saw it); receipt ok | 3/5 | 9.3 | 0.0925 |  |
