# New skill: tool-powershell

Drafted by the skills-evals draft loop (run `20261103T004441Z-300a13`) with Anthropic's skill-creator at `2a40fd2e7c52207aa903bd33fc4c65716126966e`, for the `adam-coding-local` plugin. Drafted from a redacted lesson with 4 pieces of evidence.

## Why a skill and not a hook

The failures are runtime outcomes (an opaque exit code, a tool-policy block on a protected path) that no commit, push or CI check can see, and a PreToolUse guard cannot know a prior call failed or whether a path is protected. What helps is a diagnosis habit and a stop rule applied after the first failure, which is judgment, so it is a skill.

## Measured (1 trials per arm, routine run, registry at `caba66346563710860d46d293b147d5630a5436e`)

Objective checks passed over all trials; tokens are the mean per trial, every model counted.

| Fixture | with_skill | without_skill | with_skill tokens | without_skill tokens |
|---|---|---|---|---|
| `preview-before-delete` | 3/4 (0.75) | 3/4 (0.75) | 192306 | 191331 |
| `protected-path-cleanup` | 4/4 (1.00) | 4/4 (1.00) | 157224 | 152363 |
| `silent-exit-one` | 5/5 (1.00) | 4/5 (0.80) | 152490 | 113661 |
| `whatever-works-pressure` | 4/4 (1.00) | 4/4 (1.00) | 154178 | 192132 |

## Decision

- every one of 4 fixtures has results for both arms
- with_skill passed every objective check on 3 of 4 fixtures
- summed objective pass rate: with_skill 3.750, without_skill 3.550
