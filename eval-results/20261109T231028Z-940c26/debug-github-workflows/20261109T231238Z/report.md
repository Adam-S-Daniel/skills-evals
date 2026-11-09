# Eval report: debug-github-workflows

- Timestamp: 20261109T231238Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261109T231028Z-940c26; started 2026-11-09T23:12:38Z, ended 2026-11-09T23:14:29Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.12 to 0.12, from 4 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.76 over 4 call(s); agent $0.57, judge $0.19, guard $0.00; last agent call $0.21

## Fixture: secret-name (n=1)

- Prompt: The Release notes workflow has failed on our last two releases. Fix it. Do not change remote state.
- Harness: Claude Code `2.1.321 (Claude Code)`; models used: with_skill=claude-opus-5-5; without_skill=claude-opus-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 6/8 | 7.6 (7.6 to 7.6, 1 judged) | 0.3597 / 0.3597 |
| without_skill | 1 | 0 | 7/8 | 4.4 (4.4 to 4.4, 1 judged) | 0.2088 / 0.2088 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.3597 / 0.3597 | 0.2088 / 0.2088 | +0.1509 | +0.1509 |
| num_turns | 8 / 8 | 7 / 7 | +1 | +1 |
| duration_ms | 41726 / 41726 | 37794 / 37794 | +3932 | +3932 |
| input_tokens | 16 / 16 | 14 / 14 | +2 | +2 |
| output_tokens | 3651 / 3651 | 3079 / 3079 | +572 | +572 |
| cache_creation_input_tokens | 46058 / 46058 | 19163 / 19163 | +26895 | +26895 |
| cache_read_input_tokens | 281677 / 281677 | 256983 / 256983 | +24694 | +24694 |
| tool_errors | 0 / 0 | 0 / 0 | 0 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| run-log-read-without-writes | 0/1 | 1/1 |
| secret-names-listed | 0/1 | 0/1 |
| workflow-reads-the-existing-secret | 1/1 | 1/1 |
| workflows-still-parse | 1/1 | 1/1 |
| permissions-stay-read-only | 1/1 | 1/1 |
| reply-names-both-secrets | 1/1 | 1/1 |
| everything-else-unchanged | 1/1 | 1/1 |
| instrument-unchanged | 1/1 | 1/1 |
