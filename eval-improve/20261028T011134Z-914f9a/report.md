## Proposed `review-bash-ci-reliability` SKILL.md edit (validation-gated)

Produced by skills-evals `scripts/propose_skill_edit.py` ([#71](https://github.com/Adam-S-Daniel/skills-evals/issues/71)). A local exhibit (skills-evals ADR 0002, decision 4): measured under the operator's own login, not badge input. Review before merging; nothing here merges itself.

- Registry: `adam-agentskills` at `9e95ab1b789ff0557b6dbd7c82726220188ef073`
- Split: train empty-repo-discovery, release-pipeline, test-runner-assertions; validation drift-report-capture (rotation 0)
- Fixed holdout: none; minimum train gain: 0.1 (normalized 0..1)
- Trials per fixture: 3, arm `with_skill`, agent model `claude-sonnet-5-5`

### Train / validation

| Fixture | Split | Baseline objective | Candidate objective | Baseline judge | Candidate judge |
|---|---|---|---|---|---|
| empty-repo-discovery | train | 21/21 | 21/21 | 9.00 | 8.47 |
| release-pipeline | train | 24/33 | 33/33 | 5.30 | 8.20 |
| test-runner-assertions | train | 19/21 | 21/21 | 6.87 | 8.93 |
| drift-report-capture | validation | 21/21 | 21/21 | 8.60 | 8.43 |

Decision: tokens 411037 -> 437526 per trial over empty-repo-discovery, release-pipeline, test-runner-assertions, drift-report-capture; candidate costs more tokens; accepted only because train gained at least the minimum; validation held and train improved.

### Body edit

Three gaps. (a) Item 5 is conditioned on seeing `commit.gpgsign = true` in config, but the runner's global config is invisible from the repo, so reviewers skip it; reword it as a requirement for every CI `git commit`, applied alongside the identity fix. (b) Item 6 lets 'pre-installed on the runner' count as verification, so a bare `jq` call is accepted; require an install step, a `command -v` guard, or replacement with plain shell. (c) Item 7's harness rule and the search heuristic only name grep/diff/cmp, so `out=$(./program ...)` in a test harness is left to abort the runner when the program under test crashes; extend the harness rule to the command under test, give a capture-status pattern, add a crash-the-subject verification step, and widen the search and How-to-Use steps accordingly.

The patch is `/tmp/claude-0/improve-results/improvements/review-bash-ci-reliability/20261028T011240Z.patch`; apply it with `git apply` at the registry root.
