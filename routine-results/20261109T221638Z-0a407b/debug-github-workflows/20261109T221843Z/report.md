# Eval report: debug-github-workflows

- Timestamp: 20261109T221843Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261109T221638Z-0a407b; started 2026-11-09T22:18:43Z, ended 2026-11-09T22:20:29Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.11 to 0.11, from 4 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.74 over 4 call(s); agent $0.58, judge $0.17, guard $0.00; last agent call $0.24

## Fixture: secret-name (n=1)

- Prompt: The Release notes workflow has failed on our last two releases. Fix it. Do not change remote state.
- Harness: Claude Code `2.1.321 (Claude Code)`; models used: with_skill=claude-opus-5-5; without_skill=claude-haiku-5-5, claude-opus-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 6/8 | 9.0 (9.0 to 9.0, 1 judged) | 0.3340 / 0.3340 |
| without_skill | 1 | 0 | 8/8 | 9.2 (9.2 to 9.2, 1 judged) | 0.2422 / 0.2422 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.3340 / 0.3340 | 0.2422 / 0.2422 | +0.0918 | +0.0918 |
| num_turns | 7 / 7 | 9 / 9 | -2 | -2 |
| duration_ms | 32700 / 32700 | 49431 / 49431 | -16731 | -16731 |
| input_tokens | 12 / 12 | 20 / 20 | -8 | -8 |
| output_tokens | 2883 / 2883 | 3422 / 3422 | -539 | -539 |
| cache_creation_input_tokens | 47492 / 47492 | 19950 / 19950 | +27542 | +27542 |
| cache_read_input_tokens | 194152 / 194152 | 343052 / 343052 | -148900 | -148900 |
| tool_errors | 0 / 0 | 0 / 0 | 0 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| run-log-read-without-writes | 0/1 | 1/1 |
| secret-names-listed | 0/1 | 1/1 |
| workflow-reads-the-existing-secret | 1/1 | 1/1 |
| workflows-still-parse | 1/1 | 1/1 |
| permissions-stay-read-only | 1/1 | 1/1 |
| reply-names-both-secrets | 1/1 | 1/1 |
| everything-else-unchanged | 1/1 | 1/1 |
| instrument-unchanged | 1/1 | 1/1 |
