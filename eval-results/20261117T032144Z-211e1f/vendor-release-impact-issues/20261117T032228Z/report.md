# Eval report: vendor-release-impact-issues

- Timestamp: 20261117T032228Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261117T032144Z-211e1f; started 2026-11-17T03:22:28Z, ended 2026-11-17T03:24:27Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.06 to 0.06, from 6 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.83 over 6 call(s); agent $0.57, judge $0.26, guard $0.00; last agent call $0.14

## Fixture: stale-draft-thin-inventory (n=3)

- Prompt: ExampleCLI 5.0.0 is out. Review its final release notes in `vendor/` against this repository, without committing, pushing or opening anything: add the review to `docs/vendor-tracking.md`, and bring `issues/` up to date as `issues/<NN>-<slug>.md` files (the issue title as the first line, `# <title>`, and the body below it), one issue per affected change. `issues/01-legacy-output-flag-removed.md` was drafted from the release candidate.
- Harness: Claude Code `2.1.326 (Claude Code)`; models used: without_skill=claude-opus-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| without_skill | 3 | 0 | 5.3/12 | 6.6 (6.4 to 6.9, 3 judged) | 0.1888 / 0.5665 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did):

| Metric (mean / median) | without_skill |
| --- | --- |
| cost_usd | 0.1888 / 0.1370 |
| num_turns | 4.7 / 4 |
| duration_ms | 25302.3 / 24549 |
| input_tokens | 8 / 8 |
| output_tokens | 2577.3 / 2455 |
| cache_creation_input_tokens | 22019.7 / 11781 |
| cache_read_input_tokens | 135716.7 / 144436 |
| tool_errors | 0.7 / 0 |

| Check (passed / scored) | without_skill |
| --- | --- |
| issues-drafted | 3/3 |
| stale-draft-rewritten-in-place | 0/3 |
| stale-draft-text-gone | 1/3 |
| cache-dir-bullet-quoted-exact | 0/3 |
| no-references-in-blockquotes | 0/3 |
| no-vendor-backlinks | 0/3 |
| ci-workflow-surface-named | 3/3 |
| release-script-surface-named | 3/3 |
| publish-time-from-published-at | 0/3 |
| lead-line-and-fixed-block | 0/3 |
| tracking-doc-gained-5-0-0 | 3/3 |
| seed-repo-unchanged | 3/3 |
