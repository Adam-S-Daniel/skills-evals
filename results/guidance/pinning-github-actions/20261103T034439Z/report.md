# Eval report: guidance/pinning-github-actions

- Modes: with_guidance_section=section, without_guidance=none, with_guidance_full=full, with_guidance_full_minus_section=full-minus-section
- Delivery: user
- Prompt: Add .github/workflows/lint.yml: on pull_request, check out the repo with actions/checkout v4.2.2, set up Node 20 with actions/setup-node v4.1.0 and run `npm run lint`. Add a second job that calls the reusable workflow example-org/shared-workflows/.github/workflows/notify.yml at v2.1.0 when lint fails. There is no network here; REFS.txt has the tags.
- Timestamp: 20261103T034439Z
- Run: billing api, runner actions, location cloud, id 41573472429; started 2026-11-03T03:44:39Z, ended 2026-11-03T03:46:53Z
- Account meter: no change recorded (API-billed run: the subscription's account meter does not apply)
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.80 over 8 call(s); agent $0.63, judge $0.00, guard $0.17; last agent call $0.18
- Harness: Claude Code `2.1.317 (Claude Code)`; models used: with_guidance_section=claude-opus-5-5; without_guidance=claude-opus-5-5; with_guidance_full=claude-haiku-5-5, claude-opus-5-5; with_guidance_full_minus_section=claude-opus-5-5

| Arm | Mode | Bytes | Guard | Objective | Judge overall | Cost (USD) | Error |
| --- | --- | --- | --- | --- | --- | --- | --- |
| with_guidance_section | section | 1869 | ok (saw it); receipt ok | 4/4 | skipped (objective-decided) | 0.1168 |  |
| without_guidance | none | 34 | ok (saw it); receipt ok | 3/4 | skipped (objective-decided) | 0.1155 |  |
| with_guidance_full | full | 25562 | ok (saw it); receipt ok | 4/4 | skipped (objective-decided) | 0.2171 |  |
| with_guidance_full_minus_section | full-minus-section | 24409 | ok (saw it); receipt ok | 3/4 | skipped (objective-decided) | 0.1808 |  |
