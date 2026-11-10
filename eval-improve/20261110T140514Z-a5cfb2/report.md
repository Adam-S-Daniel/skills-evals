## Proposed `workflow-path-audit` SKILL.md edit (validation-gated)

Produced by skills-evals `scripts/propose_skill_edit.py --trim-description` ([#687](https://github.com/Adam-S-Daniel/skills-evals/issues/687)): the description was over adam-agentskills' 400-character listing cap, so its `length-limit` waiver is removed here too. Only the description changed; the body is unchanged. A local exhibit (skills-evals ADR 0002, decision 4), not badge input.

- Registry: `adam-agentskills` at `31e613b9aa9eb4a7f7d7b2bd575b64635d2a5739`
- Length: 425 -> 392 characters
- Measured: every fixture, 3 trial(s) each, `with_skill` arm on `claude-sonnet-5-5`, no judge; proposal model `claude-fable-5-2`

### Description

Before: Audit GitHub Actions workflows for salient-path conditionals — every workflow that triggers on pull_request or push must filter on the files and directories its steps actually depend on, and skip with success when nothing salient changed. Use when adding a new workflow, modifying an existing one's steps, renaming/moving files a workflow depends on, or when a CI bill spike points at workflows running on irrelevant changes.

After: Audit GitHub Actions workflows for salient-path conditionals: every workflow triggered on pull_request or push must filter on the files/directories its steps depend on and skip with success when nothing salient changed. Use when adding a workflow, modifying a workflow's steps, renaming/moving files a workflow depends on, or a CI bill spike points at workflows running on irrelevant changes.

### Objective checks passed

| Fixture | Baseline | Candidate |
|---|---|---|
| `companion-skip-pair` | 24/24 | 24/24 |
| `moved-test-dir` | 30/30 | 30/30 |
| `required-by-unseen-ruleset` | 33/33 | 33/33 |
| `required-check-routing` | 24/24 | 24/24 |
| `required-gate-salience` | 35/36 | 36/36 |
| `workflow-doc-in-step` | 30/30 | 30/30 |

Acceptance rule: the candidate passes at least as many checks as the baseline summed over every fixture, and no fixture loses more than 1. Decision: objective checks passed over all fixtures 176/177 -> 177/177; no worse in aggregate, and no fixture lost more than 1 check(s).

The patch is `/tmp/tmp.2GAjBjKpqI/improvements/workflow-path-audit/20261110T140717Z.patch`; apply it with `git apply` at the registry root.
