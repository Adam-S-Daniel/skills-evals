# New skill: red-ci-adamdaniel-ai

Drafted by the skills-evals draft loop (run `20261103T003800Z-5baf20`) with Anthropic's skill-creator at `2a40fd2e7c52207aa903bd33fc4c65716126966e`, for the `adam-coding-anywhere` plugin. Drafted from a redacted lesson with 54 pieces of evidence.

## Why a skill and not a hook

Whether a push leaves CI red is only known after the run finishes, so no pre-commit, pre-push or PreToolUse check can refuse it; the lesson is a diagnosis procedure over run conclusions and workflow shape.

## Measured (1 trials per arm, routine run, registry at `caba66346563710860d46d293b147d5630a5436e`)

Objective checks passed over all trials; tokens are the mean per trial, every model counted.

| Fixture | with_skill | without_skill | with_skill tokens | without_skill tokens |
|---|---|---|---|---|
| `concurrency-cancel` | 2/2 (1.00) | 1/2 (0.50) | 190047 | 187331 |
| `paths-required` | 2/3 (0.67) | 3/3 (1.00) | 190825 | 186132 |
| `timeout-wall` | 3/3 (1.00) | 2/3 (0.67) | 191072 | 185386 |
| `unpinned-action` | 2/2 (1.00) | 1/2 (0.50) | 227332 | 185601 |

## Decision

- every one of 4 fixtures has results for both arms
- with_skill passed every objective check on 3 of 4 fixtures
- summed objective pass rate: with_skill 3.667, without_skill 2.667
