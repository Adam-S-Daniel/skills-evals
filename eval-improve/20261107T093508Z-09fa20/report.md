## Proposed `fan-out-triage` SKILL.md edit (validation-gated)

Produced by skills-evals `scripts/propose_skill_edit.py --trim-description` ([#687](https://github.com/Adam-S-Daniel/skills-evals/issues/687)): the description was over adam-agentskills' 400-character listing cap, so its `length-limit` waiver is removed here too. Only the description changed; the body is unchanged. A local exhibit (skills-evals ADR 0002, decision 4), not badge input.

- Registry: `adam-agentskills` at `1434f6275008641111cf8f88c506e0cb54382b37`
- Length: 480 -> 397 characters
- Measured: every fixture, 3 trial(s) each, `with_skill` arm on `claude-sonnet-5-5`, no judge; proposal model `claude-fable-5-1`

### Description

Before: Triage a large list of items (release-note bullets, issues, alerts, findings; dozens to thousands) against one or more repos by fanning the work out to parallel subagents, without letting ID drift or a thin inventory corrupt the result. Use when asked to go through a changelog, backlog or report and decide which items affect your code, especially if you are about to split the list across agents. Not for a list you can read in one sitting, or for reviewing one dependency bump.

After: Triage a large list of items (release notes, issues, alerts, findings; dozens to thousands) against one or more repos with parallel subagents, guarding against ID drift and a thin inventory. Use when asked to go through a changelog, backlog or report and decide which items affect your code, especially before splitting across agents. Not for a list readable in one sitting or one dependency bump.

### Objective checks passed

| Fixture | Baseline | Candidate |
|---|---|---|
| `keyword-lookalikes` | 21/21 | 21/21 |
| `shifted-draft` | 11/15 | 15/15 |
| `single-file` | 18/18 | 17/18 |
| `three-files` | 19/21 | 20/21 |

Acceptance rule: the candidate passes at least as many checks as the baseline summed over every fixture, and no fixture loses more than 1. Decision: objective checks passed over all fixtures 69/75 -> 73/75; no worse in aggregate, and no fixture lost more than 1 check(s).

The patch is `/tmp/tmp.StNk6DjQBU/improvements/fan-out-triage/20261107T093621Z.patch`; apply it with `git apply` at the registry root.
