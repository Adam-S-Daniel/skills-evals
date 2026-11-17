# Eval report: vendor-release-impact-issues

- Timestamp: 20261117T032428Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261117T032144Z-211e1f; started 2026-11-17T03:24:28Z, ended 2026-11-17T03:26:06Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.06 to 0.06, from 6 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.40 over 6 call(s); agent $0.28, judge $0.12, guard $0.00; last agent call $0.07

## Fixture: stale-draft-thin-inventory (n=3)

- Prompt: ExampleCLI 5.0.0 is out. Review its final release notes in `vendor/` against this repository, without committing, pushing or opening anything: add the review to `docs/vendor-tracking.md`, and bring `issues/` up to date as `issues/<NN>-<slug>.md` files (the issue title as the first line, `# <title>`, and the body below it), one issue per affected change. `issues/01-legacy-output-flag-removed.md` was drafted from the release candidate.
- Harness: Claude Code `2.1.326 (Claude Code)`; models used: without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| without_skill | 3 | 0 | 5.7/12 | 6.6 (6.4 to 6.9, 3 judged) | 0.0943 / 0.2828 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did):

| Metric (mean / median) | without_skill |
| --- | --- |
| cost_usd | 0.0943 / 0.0779 |
| num_turns | 5.7 / 5 |
| duration_ms | 18972.7 / 18044 |
| input_tokens | 11.3 / 10 |
| output_tokens | 2117 / 2117 |
| cache_creation_input_tokens | 21242.7 / 11695 |
| cache_read_input_tokens | 199823.3 / 183401 |
| tool_errors | 0.3 / 0 |

| Check (passed / scored) | without_skill |
| --- | --- |
| issues-drafted | 3/3 |
| stale-draft-rewritten-in-place | 0/3 |
| stale-draft-text-gone | 2/3 |
| cache-dir-bullet-quoted-exact | 0/3 |
| no-references-in-blockquotes | 0/3 |
| no-vendor-backlinks | 0/3 |
| ci-workflow-surface-named | 3/3 |
| release-script-surface-named | 3/3 |
| publish-time-from-published-at | 0/3 |
| lead-line-and-fixed-block | 0/3 |
| tracking-doc-gained-5-0-0 | 3/3 |
| seed-repo-unchanged | 3/3 |
