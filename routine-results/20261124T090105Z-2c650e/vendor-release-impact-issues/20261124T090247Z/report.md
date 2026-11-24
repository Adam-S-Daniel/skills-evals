# Eval report: vendor-release-impact-issues

- Timestamp: 20261124T090247Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261124T090105Z-2c650e; started 2026-11-24T09:02:47Z, ended 2026-11-24T09:03:54Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.06 to 0.06, from 2 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.32 over 2 call(s); agent $0.32, judge $0.00, guard $0.00; last agent call $0.14
- Estimated allowance (approximate, from token counts by type, weight table 2026-11-20): 0.02 points of the weekly meter (0.01 to 0.03); Fable meter 0.00 points

## Fixture: stale-draft-thin-inventory (n=1)

- Prompt: ExampleCLI 5.0.0 is out. Review its final release notes in `vendor/` against this repository, without committing, pushing or opening anything: add the review to `docs/vendor-tracking.md`, and bring `issues/` up to date as `issues/<NN>-<slug>.md` files (the issue title as the first line, `# <title>`, and the body below it), one issue per affected change. `issues/01-legacy-output-flag-removed.md` was drafted from the release candidate.
- Harness: Claude Code `2.1.331 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 12/12 | skipped: the version with the skill passed more checks (12 of 12 vs 5 of 12) | 0.1798 / 0.1798 |
| without_skill | 1 | 0 | 5/12 | skipped: the version with the skill passed more checks (12 of 12 vs 5 of 12) | 0.1389 / 0.1389 |

Judge: when the version with the skill or guidance passes more checks than its partner, the judge isn't needed and both are skipped. On a tie or a loss, the judge scores both from 0 to 10.

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1798 / 0.1798 | 0.1389 / 0.1389 | +0.0408 | +0.0408 |
| num_turns | 7 / 7 | 5 / 5 | +2 | +2 |
| duration_ms | 33063 / 33063 | 24493 / 24493 | +8570 | +8570 |
| input_tokens | 12 / 12 | 10 / 10 | +2 | +2 |
| output_tokens | 3969 / 3969 | 2246 / 2246 | +1723 | +1723 |
| cache_creation_input_tokens | 30803 / 30803 | 24993 / 24993 | +5810 | +5810 |
| cache_read_input_tokens | 168400 / 168400 | 164875 / 164875 | +3525 | +3525 |
| tool_errors | 0 / 0 | 0 / 0 | 0 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| issues-drafted | 1/1 | 1/1 |
| stale-draft-rewritten-in-place | 1/1 | 0/1 |
| stale-draft-text-gone | 1/1 | 0/1 |
| cache-dir-bullet-quoted-exact | 1/1 | 0/1 |
| no-references-in-blockquotes | 1/1 | 0/1 |
| no-vendor-backlinks | 1/1 | 0/1 |
| ci-workflow-surface-named | 1/1 | 1/1 |
| release-script-surface-named | 1/1 | 1/1 |
| publish-time-from-published-at | 1/1 | 0/1 |
| lead-line-and-fixed-block | 1/1 | 0/1 |
| tracking-doc-gained-5-0-0 | 1/1 | 1/1 |
| seed-repo-unchanged | 1/1 | 1/1 |
