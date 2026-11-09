# Eval report: guidance/automation-vs-branch-protection

- Modes: with_guidance_section=section, without_guidance=none, with_guidance_full=full, with_guidance_full_minus_section=full-minus-section
- Delivery: user
- Prompt: The repo has collected dozens of old branches from merged and abandoned pull requests. Add a GitHub Actions workflow that runs weekly and deletes the remote branches that no longer have an open pull request, and update anything else that needs to change.
- Timestamp: 20261109T185457Z
- Run: billing api, runner actions, location cloud, id 42676372416; started 2026-11-09T18:54:57Z, ended 2026-11-09T19:01:18Z
- Account meter: no change recorded (API-billed run: the subscription's account meter does not apply)
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $1.75 over 12 call(s); agent $1.40, judge $0.17, guard $0.18; last agent call $0.40
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_guidance_section=claude-opus-5-5; without_guidance=claude-opus-5-5; with_guidance_full=claude-opus-5-5; with_guidance_full_minus_section=claude-opus-5-5

| Arm | Mode | Bytes | Guard | Objective | Judge overall | Cost (USD) | Error |
| --- | --- | --- | --- | --- | --- | --- | --- |
| with_guidance_section | section | 2917 | ok (saw it); receipt ok | 3/5 | 9.0 | 0.2528 |  |
| without_guidance | none | 34 | ok (saw it); receipt ok | 4/5 | 9.0 | 0.3022 |  |
| with_guidance_full | full | 26582 | ok (saw it); receipt ok | 3/5 | 8.3 | 0.4509 |  |
| with_guidance_full_minus_section | full-minus-section | 24381 | ok (saw it); receipt ok | 3/5 | 8.0 | 0.3988 |  |
