# Eval report: debug-github-workflows

- Timestamp: 20261108T130249Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261108T125656Z-b73382; started 2026-11-08T13:02:49Z, ended 2026-11-08T13:04:03Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.76 to 0.76, from 4 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.31 over 4 call(s); agent $0.22, judge $0.10, guard $0.00; last agent call $0.09

## Fixture: swallowed-failure (n=1)

- Prompt: The nightly Sync labels workflow has been green all week, but the triage and needs-review labels never showed up on any of our repositories. Find out why and fix it. Do not change remote state.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 7/7 | 8.2 (8.2 to 8.2, 1 judged) | 0.1295 / 0.1295 |
| without_skill | 1 | 0 | 7/7 | 7.0 (7.0 to 7.0, 1 judged) | 0.0887 / 0.0887 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1295 / 0.1295 | 0.0887 / 0.0887 | +0.0408 | +0.0408 |
| num_turns | 5 / 5 | 5 / 5 | 0 | 0 |
| duration_ms | 18611 / 18611 | 26418 / 26418 | -7807 | -7807 |
| input_tokens | 10 / 10 | 10 / 10 | 0 | 0 |
| output_tokens | 1664 / 1664 | 1911 / 1911 | -247 | -247 |
| cache_creation_input_tokens | 24244 / 24244 | 13183 / 13183 | +11061 | +11061 |
| cache_read_input_tokens | 158325 / 158325 | 168509 / 168509 | -10184 | -10184 |
| tool_errors | 1 / 1 | 0 / 0 | +1 | +1 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| no-remote-write | 1/1 | 1/1 |
| working-listing-syncs-every-label | 1/1 | 1/1 |
| failed-listing-fails-the-script | 1/1 | 1/1 |
| reply-names-the-swallowing-construct | 1/1 | 1/1 |
| reply-names-the-missing-flag | 1/1 | 1/1 |
| workflow-and-inputs-unchanged | 1/1 | 1/1 |
| instrument-unchanged | 1/1 | 1/1 |
