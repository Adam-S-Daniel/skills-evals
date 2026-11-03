# New skill: tool-powershell

Drafted by the skills-evals draft loop (run `20261103T004933Z-2f7f37`) with Anthropic's skill-creator at `2a40fd2e7c52207aa903bd33fc4c65716126966e`, for the `adam-coding-local` plugin. Drafted from a redacted lesson with 4 pieces of evidence.

## Why a skill and not a hook

The failures are runtime tool errors (a generic exit code 1, a harness-blocked delete of a protected path); no commit, push or CI input shows them, and a PreToolUse guard cannot tell a bad PowerShell command from a good one without running it.

## Measured (1 trials per arm, routine run, registry at `caba66346563710860d46d293b147d5630a5436e`)

Objective checks passed over all trials; tokens are the mean per trial, every model counted.

| Fixture | with_skill | without_skill | with_skill tokens | without_skill tokens |
|---|---|---|---|---|
| `bash-quoting` | 4/4 (1.00) | 4/4 (1.00) | 115128 | 112237 |
| `new-script` | 3/4 (0.75) | 3/4 (0.75) | 75096 | 74631 |
| `protected-path` | 2/3 (0.67) | 1/3 (0.33) | 117175 | 190753 |
| `silent-exit` | 4/4 (1.00) | 3/4 (0.75) | 115757 | 150269 |

## Decision

- every one of 4 fixtures has results for both arms
- with_skill passed every objective check on 2 of 4 fixtures
- summed objective pass rate: with_skill 3.417, without_skill 2.833
