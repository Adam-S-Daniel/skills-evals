# Eval report: guidance/pinning-github-actions

- Modes: with_guidance_section=section, without_guidance=none, with_guidance_full=full, with_guidance_full_minus_section=full-minus-section
- Delivery: user
- Prompt: Add .github/workflows/lint.yml: on pull_request, check out the repo with actions/checkout v4.2.2, set up Node 20 with actions/setup-node v4.1.0 and run `npm run lint`. Add a second job that calls the reusable workflow example-org/shared-workflows/.github/workflows/notify.yml at v2.1.0 when lint fails. There is no network here; REFS.txt has the tags.
- Timestamp: 20261103T022515Z
- Run: billing api, runner actions, location cloud, id 41565470204; started 2026-11-03T02:25:15Z, ended 2026-11-03T02:26:19Z
- Account meter: no change recorded (API-billed run: the subscription's account meter does not apply)
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.33 over 8 call(s); agent $0.24, judge $0.00, guard $0.09; last agent call $0.08
- Harness: Claude Code `2.1.317 (Claude Code)`; models used: with_guidance_section=claude-sonnet-5-5; without_guidance=claude-sonnet-5-5; with_guidance_full=claude-sonnet-5-5; with_guidance_full_minus_section=claude-sonnet-5-5

| Arm | Mode | Bytes | Guard | Objective | Judge overall | Cost (USD) | Error |
| --- | --- | --- | --- | --- | --- | --- | --- |
| with_guidance_section | section | 1869 | ok (saw it); receipt ok | 4/4 | skipped (objective-decided) | 0.0466 |  |
| without_guidance | none | 34 | ok (saw it); receipt ok | 3/4 | skipped (objective-decided) | 0.0441 |  |
| with_guidance_full | full | 25562 | ok (saw it); receipt ok | 4/4 | skipped (objective-decided) | 0.0734 |  |
| with_guidance_full_minus_section | full-minus-section | 24409 | ok (saw it); receipt ok | 3/4 | skipped (objective-decided) | 0.0752 |  |
