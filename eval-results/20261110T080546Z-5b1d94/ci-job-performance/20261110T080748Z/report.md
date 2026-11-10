# Eval report: ci-job-performance

- Timestamp: 20261110T080748Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261110T080546Z-5b1d94; started 2026-11-10T08:07:48Z, ended 2026-11-10T08:11:55Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.2 to 0.2, from 6 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $1.26 over 6 call(s); agent $0.96, judge $0.30, guard $0.00; last agent call $0.26

## Fixture: act-local-loop (n=3)

- Prompt: Today is 2026-11-07. We want to run this repository's `ci` workflow locally with act before pushing, so a broken change shows up before CI. `scripts/install-act.sh` and `scripts/local-ci.sh` are our first attempt: the `build` job's upload step fails under act, and the two scripts pick whatever act and runner image happen to be newest. The mirror's act releases and runner images are listed in `tools/`. Fix the scripts so the local loop works and is reproducible, and tell us what the loop is good for (we also hope it will tell us how long CI will take).
- Harness: Claude Code `2.1.322 (Claude Code)`; models used: without_skill=claude-opus-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| without_skill | 3 | 0 | 2/5 | 7.4 (6.0 to 8.2, 3 judged) | 0.3187 / 0.9562 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did):

| Metric (mean / median) | without_skill |
| --- | --- |
| cost_usd | 0.3187 / 0.2840 |
| num_turns | 9 / 9 |
| duration_ms | 69434.7 / 70529 |
| input_tokens | 16.7 / 16 |
| output_tokens | 6369 / 6430 |
| cache_creation_input_tokens | 25609 / 16612 |
| cache_read_input_tokens | 316135.7 / 312335 |
| tool_errors | 2.7 / 3 |

| Check (passed / scored) | without_skill |
| --- | --- |
| act-release-pinned-and-verified | 0/3 |
| runner-image-pinned-by-digest | 0/3 |
| artifact-server-path-given | 3/3 |
| workflow-still-uploads-the-artifact | 3/3 |
| lists-pages-and-build-scripts-unchanged | 0/3 |
