# Eval report: guidance/pinning-github-actions

- Modes: with_guidance_full=full, with_guidance_full_minus_section=full-minus-section
- Delivery: user
- Prompt: Add .github/workflows/lint.yml: on pull_request, check out the repo with actions/checkout v4.2.2, set up Node 20 with actions/setup-node v4.1.0 and run `npm run lint`. Add a second job that calls the reusable workflow example-org/shared-workflows/.github/workflows/notify.yml at v2.1.0 when lint fails. There is no network here; REFS.txt has the tags.
- Timestamp: 20261117T132020Z
- Run: billing subscription, runner routine, location cloud, id 20261117T131934Z-14d5a5; started 2026-11-17T13:20:20Z, ended 2026-11-17T13:21:16Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.08 to 0.08, from 6 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.22 over 6 call(s); agent $0.15, judge $0.00, guard $0.07; last agent call $0.08
- Harness: Claude Code `2.1.326 (Claude Code)`; models used: with_guidance_full=claude-sonnet-5-5; with_guidance_full_minus_section=claude-sonnet-5-5

| Arm | Mode | Pair | Bytes | Guard | Objective | Judge overall | Cost (USD) | Error |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| with_guidance_full | full | in context | 26653 | ok (saw it); receipt ok | 4/4 | 8.0 | 0.0757 |  |
| with_guidance_full_minus_section | full-minus-section | in context | 25500 | ok (saw it); receipt ok | 4/4 | 8.0 | 0.0764 |  |

Judge: when the version with the skill or guidance passes more checks than its partner, the judge isn't needed and both are skipped. On a tie or a loss, the judge scores both from 0 to 10.
