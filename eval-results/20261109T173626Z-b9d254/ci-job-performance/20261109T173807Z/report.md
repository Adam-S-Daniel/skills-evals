# Eval report: ci-job-performance

- Timestamp: 20261109T173807Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261109T173626Z-b9d254; started 2026-11-09T17:38:07Z, ended 2026-11-09T17:40:00Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.02 to 0.02, from 6 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.32 over 6 call(s); agent $0.22, judge $0.10, guard $0.00; last agent call $0.07

## Fixture: act-local-loop (n=3)

- Prompt: Today is 2026-11-07. We want to run this repository's `ci` workflow locally with act before pushing, so a broken change shows up before CI. `scripts/install-act.sh` and `scripts/local-ci.sh` are our first attempt: the `build` job's upload step fails under act, and the two scripts pick whatever act and runner image happen to be newest. The mirror's act releases and runner images are listed in `tools/`. Fix the scripts so the local loop works and is reproducible, and tell us what the loop is good for (we also hope it will tell us how long CI will take).
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| without_skill | 3 | 0 | 3.7/5 | 7.0 (5.0 to 8.2, 3 judged) | 0.0725 / 0.2174 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did):

| Metric (mean / median) | without_skill |
| --- | --- |
| cost_usd | 0.0725 / 0.0663 |
| num_turns | 4.7 / 4 |
| duration_ms | 27222.3 / 22886 |
| input_tokens | 9.3 / 8 |
| output_tokens | 2544 / 2438 |
| cache_creation_input_tokens | 11993.3 / 11177 |
| cache_read_input_tokens | 170368.3 / 142688 |
| tool_errors | 1 / 1 |

| Check (passed / scored) | without_skill |
| --- | --- |
| act-release-pinned-and-verified | 2/3 |
| runner-image-pinned-by-digest | 0/3 |
| artifact-server-path-given | 3/3 |
| workflow-still-uploads-the-artifact | 3/3 |
| lists-pages-and-build-scripts-unchanged | 3/3 |
