# New skill: red-ci-adamdaniel-ai

Drafted by the skills-evals draft loop (run `20261103T004309Z-6eb876`) with Anthropic's skill-creator at `2a40fd2e7c52207aa903bd33fc4c65716126966e`, for the `adam-coding-anywhere` plugin. Drafted from a redacted lesson with 54 pieces of evidence.

## Why a skill and not a hook

Red CI after a push cannot be refused at commit or push time: the failure appears only after the push, and telling a superseded run from a real failure, or a stub's green from the real lane's, needs reading job output and judging it.

## Measured (1 trials per arm, routine run, registry at `caba66346563710860d46d293b147d5630a5436e`)

Objective checks passed over all trials; tokens are the mean per trial, every model counted.

| Fixture | with_skill | without_skill | with_skill tokens | without_skill tokens |
|---|---|---|---|---|
| `cancelled-required-check` | 3/3 (1.00) | 3/3 (1.00) | 115299 | 112860 |
| `missing-secret` | 3/4 (0.75) | 4/4 (1.00) | 114446 | 111978 |
| `pin-skew` | 3/3 (1.00) | 2/3 (0.67) | 114653 | 148448 |
| `stub-green-mixed-pr` | 3/3 (1.00) | 3/3 (1.00) | 112861 | 112414 |

## Decision

- every one of 4 fixtures has results for both arms
- with_skill passed every objective check on 3 of 4 fixtures
- summed objective pass rate: with_skill 3.750, without_skill 3.667
