# Eval report: guidance/pinning-github-actions

- Modes: with_guidance_section=section, without_guidance=none, with_guidance_full=full, with_guidance_full_minus_section=full-minus-section
- Delivery: user
- Prompt: Add .github/workflows/lint.yml: on pull_request, check out the repo with actions/checkout v4.2.2, set up Node 20 with actions/setup-node v4.1.0 and run `npm run lint`. Add a second job that calls the reusable workflow example-org/shared-workflows/.github/workflows/notify.yml at v2.1.0 when lint fails. There is no network here; REFS.txt has the tags.
- Timestamp: 20261101T155200Z
- Run: billing subscription, runner routine, location cloud, id 20261101T155105Z-e2ce40; started 2026-11-01T15:52:00Z, ended 2026-11-01T15:53:45Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.88 to 0.88, from 8 snapshots
- Harness: Claude Code `2.1.316 (Claude Code)`; models used: with_guidance_section=claude-sonnet-5-5; without_guidance=claude-sonnet-5-5; with_guidance_full=claude-sonnet-5-5; with_guidance_full_minus_section=claude-sonnet-5-5

| Arm | Mode | Bytes | Guard | Objective | Judge overall | Cost (USD) | Error |
| --- | --- | --- | --- | --- | --- | --- | --- |
| with_guidance_section | section | 1869 | ok (saw it); receipt ok | 4/4 | skipped (objective-decided) | 0.0625 |  |
| without_guidance | none | 34 | ok (saw it); receipt ok | 3/4 | skipped (objective-decided) | 0.0587 |  |
| with_guidance_full | full | 25222 | ok (saw it); receipt ok | 4/4 | skipped (objective-decided) | 0.1054 |  |
| with_guidance_full_minus_section | full-minus-section | 24069 | ok (saw it); receipt ok | 3/4 | skipped (objective-decided) | 0.1045 |  |
