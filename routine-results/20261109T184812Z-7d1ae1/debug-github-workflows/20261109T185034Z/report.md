# Eval report: debug-github-workflows

- Timestamp: 20261109T185034Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261109T184812Z-7d1ae1; started 2026-11-09T18:50:34Z, ended 2026-11-09T18:52:25Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.04 to 0.04, from 4 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.77 over 4 call(s); agent $0.56, judge $0.21, guard $0.00; last agent call $0.21

## Fixture: secret-name (n=1)

- Prompt: The Release notes workflow has failed on our last two releases. Fix it. Do not change remote state.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-haiku-5-5, claude-opus-5-5; without_skill=claude-opus-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 6/8 | error | 0.3534 / 0.3534 |
| without_skill | 1 | 0 | 6/8 | 5.0 (5.0 to 5.0, 1 judged) | 0.2081 / 0.2081 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.3534 / 0.3534 | 0.2081 / 0.2081 | +0.1452 | +0.1452 |
| num_turns | 7 / 7 | 7 / 7 | 0 | 0 |
| duration_ms | 51446 / 51446 | 31150 / 31150 | +20296 | +20296 |
| input_tokens | 16 / 16 | 12 / 12 | +4 | +4 |
| output_tokens | 3498 / 3498 | 2746 / 2746 | +752 | +752 |
| cache_creation_input_tokens | 45899 / 45899 | 21691 / 21691 | +24208 | +24208 |
| cache_read_input_tokens | 242117 / 242117 | 223528 / 223528 | +18589 | +18589 |
| tool_errors | 0 / 0 | 1 / 1 | -1 | -1 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| run-log-read-without-writes | 0/1 | 0/1 |
| secret-names-listed | 0/1 | 0/1 |
| workflow-reads-the-existing-secret | 1/1 | 1/1 |
| workflows-still-parse | 1/1 | 1/1 |
| permissions-stay-read-only | 1/1 | 1/1 |
| reply-names-both-secrets | 1/1 | 1/1 |
| everything-else-unchanged | 1/1 | 1/1 |
| instrument-unchanged | 1/1 | 1/1 |
