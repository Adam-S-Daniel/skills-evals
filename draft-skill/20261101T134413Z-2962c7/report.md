# New skill: fan-out-triage

Drafted by the skills-evals draft loop (run `20261101T134413Z-2962c7`) with Anthropic's skill-creator at `2a40fd2e7c52207aa903bd33fc4c65716126966e`, for the `adam-coding-anywhere` plugin. Drafted from a redacted lesson with 1 pieces of evidence.

## Why a skill and not a hook

Whether a triage candidate is real needs reading the source item against the repo, and chunking or inventory quality is judgment; a commit, push or CI check cannot see how an agent fanned out work.

## Measured (1 trials per arm, routine run, registry at `c0030df6f6306950a23c4e4e948f106ed62b2546`)

Objective checks passed over all trials; tokens are the mean per trial, every model counted.

| Fixture | with_skill | without_skill | with_skill tokens | without_skill tokens |
|---|---|---|---|---|
| `keyword-lookalikes` | 7/7 (1.00) | 1/7 (0.14) | 240864 | 229394 |
| `shifted-draft` | 5/5 (1.00) | 1/5 (0.20) | 243092 | 156285 |
| `single-file` | 5/6 (0.83) | 1/6 (0.17) | 161042 | 192576 |
| `three-files` | 6/7 (0.86) | 1/7 (0.14) | 203019 | 197189 |

## Decision

- every one of 4 fixtures has results for both arms
- with_skill passed every objective check on 2 of 4 fixtures
- summed objective pass rate: with_skill 3.690, without_skill 0.652
