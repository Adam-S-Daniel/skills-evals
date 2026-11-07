# Eval report: ci-job-performance

- Timestamp: 20261107T232111Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261107T231934Z-ca27bd; started 2026-11-07T23:21:11Z, ended 2026-11-07T23:22:10Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.7 to 0.7, from 2 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.26 over 2 call(s); agent $0.26, judge $0.00, guard $0.00; last agent call $0.09

## Fixture: act-local-loop (n=1)

- Prompt: Today is 2026-11-07. We want to run this repository's `ci` workflow locally with act before pushing, so a broken change shows up before CI. `scripts/install-act.sh` and `scripts/local-ci.sh` are our first attempt: the `build` job's upload step fails under act, and the two scripts pick whatever act and runner image happen to be newest. The mirror's act releases and runner images are listed in `tools/`. Fix the scripts so the local loop works and is reproducible, and tell us what the loop is good for (we also hope it will tell us how long CI will take).
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 5/5 | skipped (objective-decided) | 0.1726 / 0.1726 |
| without_skill | 1 | 0 | 4/5 | skipped (objective-decided) | 0.0868 / 0.0868 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1726 / 0.1726 | 0.0868 / 0.0868 | +0.0858 | +0.0858 |
| num_turns | 7 / 7 | 3 / 3 | +4 | +4 |
| duration_ms | 34245 / 34245 | 21418 / 21418 | +12827 | +12827 |
| input_tokens | 12 / 12 | 6 / 6 | +6 | +6 |
| output_tokens | 3394 / 3394 | 2299 / 2299 | +1095 | +1095 |
| cache_creation_input_tokens | 30232 / 30232 | 13492 / 13492 | +16740 | +16740 |
| cache_read_input_tokens | 177072 / 177072 | 97866 / 97866 | +79206 | +79206 |
| tool_errors | 2 / 2 | 1 / 1 | +1 | +1 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| act-release-pinned-and-verified | 1/1 | 1/1 |
| runner-image-pinned-by-digest | 1/1 | 0/1 |
| artifact-server-path-given | 1/1 | 1/1 |
| workflow-still-uploads-the-artifact | 1/1 | 1/1 |
| lists-pages-and-build-scripts-unchanged | 1/1 | 1/1 |
