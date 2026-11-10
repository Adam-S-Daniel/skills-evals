# Eval report: debug-github-workflows

- Timestamp: 20261110T013031Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261110T012654Z-f4db93; started 2026-11-10T01:30:31Z, ended 2026-11-10T01:31:44Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.14 to 0.14, from 2 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.53 over 2 call(s); agent $0.53, judge $0.00, guard $0.00; last agent call $0.18

## Fixture: secret-name (n=1)

- Prompt: The Release notes workflow has failed on our last two releases. Fix it. Do not change remote state.
- Harness: Claude Code `2.1.321 (Claude Code)`; models used: with_skill=claude-opus-5-5; without_skill=claude-opus-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 7/8 | skipped: the version with the skill passed more checks (7 of 8 vs 6 of 8) | 0.3430 / 0.3430 |
| without_skill | 1 | 0 | 6/8 | skipped: the version with the skill passed more checks (7 of 8 vs 6 of 8) | 0.1828 / 0.1828 |

Judge: when the version with the skill or guidance passes more checks than its partner, the judge isn't needed and both are skipped. On a tie or a loss, the judge scores both from 0 to 10.

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.3430 / 0.3430 | 0.1828 / 0.1828 | +0.1601 | +0.1601 |
| num_turns | 8 / 8 | 6 / 6 | +2 | +2 |
| duration_ms | 38062 / 38062 | 32103 / 32103 | +5959 | +5959 |
| input_tokens | 16 / 16 | 12 / 12 | +4 | +4 |
| output_tokens | 2891 / 2891 | 2436 / 2436 | +455 | +455 |
| cache_creation_input_tokens | 45636 / 45636 | 18179 / 18179 | +27457 | +27457 |
| cache_read_input_tokens | 284480 / 284480 | 215751 / 215751 | +68729 | +68729 |
| tool_errors | 0 / 0 | 0 / 0 | 0 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| run-log-read-without-writes | 0/1 | 0/1 |
| secret-names-listed | 1/1 | 0/1 |
| workflow-reads-the-existing-secret | 1/1 | 1/1 |
| workflows-still-parse | 1/1 | 1/1 |
| permissions-stay-read-only | 1/1 | 1/1 |
| reply-names-both-secrets | 1/1 | 1/1 |
| everything-else-unchanged | 1/1 | 1/1 |
| instrument-unchanged | 1/1 | 1/1 |
