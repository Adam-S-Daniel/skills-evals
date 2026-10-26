# Eval report: review-bash-ci-reliability

- Timestamp: 20261026T033941Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261026T033629Z-1e78b2; started 2026-10-26T03:39:41Z, ended 2026-10-26T04:08:17Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent call starts, so the 7 call(s) from the last reading on are not in it): five_hour 0.02 to 0.05, seven_day 0.54 to 0.54, from 9 snapshots

## Fixture: review-bash-ci-reliability (n=3)

- Prompt: Review the shell in this repo's CI for reliability problems and fix what you find.
- Harness: Claude Code `2.1.310 (Claude Code)`; models used: with_skill=claude-opus-5-5, claude-sonnet-5-5; without_skill=claude-haiku-5-5, claude-opus-5-5, claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 3 | 0 | 6/11 | 4.3 (4.2 to 4.4, 2 judged); 1 judge error(s) | 0.7915 / 2.3746 |
| without_skill | 3 | 0 | 6/11 | 3.6 (2.5 to 4.2, 3 judged) | 0.8704 / 2.6112 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.7915 / 0.7977 | 0.8704 / 0.8544 | -0.0789 | -0.0568 |
| num_turns | 10.7 / 10 | 10.3 / 12 | +0.3 | -2 |
| duration_ms | 185106.3 / 182987 | 227274.7 / 228637 | -42168.3 | -45650 |
| input_tokens | 18.7 / 18 | 20.7 / 24 | -2 | -6 |
| output_tokens | 11722 / 12121 | 12719.3 / 12379 | -997.3 | -258 |
| cache_creation_input_tokens | 39219 / 39225 | 38931 / 42657 | +288 | -3432 |
| cache_read_input_tokens | 404490.7 / 368782 | 470095.3 / 514929 | -65604.7 | -146147 |
| tool_errors | 0.7 / 0 | 2.3 / 1 | -1.7 | -1 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| workflow-yaml-parses | 3/3 | 3/3 |
| workflow-file-present | 3/3 | 3/3 |
| process-substitution-error-propagates | 2/3 | 2/3 |
| grep-q-avoids-broken-pipe | 2/3 | 2/3 |
| gh-api-failure-not-swallowed | 2/3 | 2/3 |
| git-identity-configured | 2/3 | 2/3 |
| jq-guaranteed-or-replaced | 0/3 | 0/3 |
| version-read-does-not-depend-on-unguarded-jq | 0/3 | 0/3 |
| commit-signing-safe-for-ci | 0/3 | 0/3 |
| decoy-optional-cleanup-untouched | 1/3 | 1/3 |
| decoy-existing-set-e-untouched | 3/3 | 3/3 |
