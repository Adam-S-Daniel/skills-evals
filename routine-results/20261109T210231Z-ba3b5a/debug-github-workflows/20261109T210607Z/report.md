# Eval report: debug-github-workflows

- Timestamp: 20261109T210607Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261109T210231Z-ba3b5a; started 2026-11-09T21:06:07Z, ended 2026-11-09T21:08:31Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.09 to 0.1, from 5 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.80 over 4 call(s); agent $0.60, judge $0.20, guard $0.00; last agent call $0.28

## Fixture: secret-name (n=1)

- Prompt: The Release notes workflow has failed on our last two releases. Fix it. Do not change remote state.
- Harness: Claude Code `2.1.321 (Claude Code)`; models used: with_skill=claude-opus-5-5; without_skill=claude-haiku-5-5, claude-opus-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 6/8 | 9.8 (9.8 to 9.8, 1 judged) | 0.3184 / 0.3184 |
| without_skill | 1 | 0 | 7/8 | 7.2 (7.2 to 7.2, 1 judged) | 0.2772 / 0.2772 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.3184 / 0.3184 | 0.2772 / 0.2772 | +0.0412 | +0.0412 |
| num_turns | 6 / 6 | 9 / 9 | -3 | -3 |
| duration_ms | 35939 / 35939 | 76981 / 76981 | -41042 | -41042 |
| input_tokens | 12 / 12 | 20 / 20 | -8 | -8 |
| output_tokens | 2880 / 2880 | 4181 / 4181 | -1301 | -1301 |
| cache_creation_input_tokens | 44324 / 44324 | 22892 / 22892 | +21432 | +21432 |
| cache_read_input_tokens | 195570 / 195570 | 350687 / 350687 | -155117 | -155117 |
| tool_errors | 0 / 0 | 1 / 1 | -1 | -1 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| run-log-read-without-writes | 0/1 | 0/1 |
| secret-names-listed | 0/1 | 1/1 |
| workflow-reads-the-existing-secret | 1/1 | 1/1 |
| workflows-still-parse | 1/1 | 1/1 |
| permissions-stay-read-only | 1/1 | 1/1 |
| reply-names-both-secrets | 1/1 | 1/1 |
| everything-else-unchanged | 1/1 | 1/1 |
| instrument-unchanged | 1/1 | 1/1 |
