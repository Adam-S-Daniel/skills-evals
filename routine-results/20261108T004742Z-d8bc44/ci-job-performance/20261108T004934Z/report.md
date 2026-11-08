# Eval report: ci-job-performance

- Timestamp: 20261108T004934Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261108T004742Z-d8bc44; started 2026-11-08T00:49:34Z, ended 2026-11-08T00:50:59Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.7 to 0.7, from 4 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.37 over 4 call(s); agent $0.27, judge $0.10, guard $0.00; last agent call $0.10

## Fixture: act-local-loop (n=1)

- Prompt: Today is 2026-11-07. We want to run this repository's `ci` workflow locally with act before pushing, so a broken change shows up before CI. `scripts/install-act.sh` and `scripts/local-ci.sh` are our first attempt: the `build` job's upload step fails under act, and the two scripts pick whatever act and runner image happen to be newest. The mirror's act releases and runner images are listed in `tools/`. Fix the scripts so the local loop works and is reproducible, and tell us what the loop is good for (we also hope it will tell us how long CI will take).
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 4/5 | 8.8 (8.8 to 8.8, 1 judged) | 0.1743 / 0.1743 |
| without_skill | 1 | 0 | 5/5 | 9.2 (9.2 to 9.2, 1 judged) | 0.0979 / 0.0979 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1743 / 0.1743 | 0.0979 / 0.0979 | +0.0764 | +0.0764 |
| num_turns | 7 / 7 | 4 / 4 | +3 | +3 |
| duration_ms | 37721 / 37721 | 27420 / 27420 | +10301 | +10301 |
| input_tokens | 12 / 12 | 8 / 8 | +4 | +4 |
| output_tokens | 3584 / 3584 | 2639 / 2639 | +945 | +945 |
| cache_creation_input_tokens | 30173 / 30173 | 14468 / 14468 | +15705 | +15705 |
| cache_read_input_tokens | 177108 / 177108 | 136002 / 136002 | +41106 | +41106 |
| tool_errors | 2 / 2 | 1 / 1 | +1 | +1 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| act-release-pinned-and-verified | 0/1 | 1/1 |
| runner-image-pinned-by-digest | 1/1 | 1/1 |
| artifact-server-path-given | 1/1 | 1/1 |
| workflow-still-uploads-the-artifact | 1/1 | 1/1 |
| lists-pages-and-build-scripts-unchanged | 1/1 | 1/1 |
