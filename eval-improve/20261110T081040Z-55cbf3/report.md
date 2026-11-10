## Proposed `vendor-release-impact-issues` SKILL.md edit (validation-gated)

Produced by skills-evals `scripts/propose_skill_edit.py --trim-description` ([#687](https://github.com/Adam-S-Daniel/skills-evals/issues/687)): the description was over adam-agentskills' 400-character listing cap, so its `length-limit` waiver is removed here too. Only the description changed; the body is unchanged. A local exhibit (skills-evals ADR 0002, decision 4), not badge input.

- Registry: `adam-agentskills` at `42f39bd8c810cfde9bab5f344b38d17fe0c5e046`
- Length: 617 -> 367 characters
- Measured: every fixture, 3 trial(s) each, `with_skill` arm on `claude-sonnet-5-5`, no judge; proposal model `claude-fable-5-2`

### Description

Before: File or rewrite GitHub issues that track how a vendor's or upstream project's release notes may affect your repos. Each issue covers one group of related changes for one affected repo, and carries exact quotes with release links and publish times, the files, pins or settings touched, the checks to run, and a fixed block for behavior that contradicts the notes. Use when asked to go through a CLI, SDK, agent, GitHub Action or library changelog and open issues for what affects you, or when a routine does. Not for reviewing a single dependency bump or Dependabot PR, or for writing your own project's release notes.

After: File or rewrite GitHub issues tracking how a vendor's or upstream project's release notes may affect your repos. Use when asked to go through a CLI, SDK, agent, GitHub Action or library changelog and open issues for what affects you, or when a routine does. Not for reviewing a single dependency bump or Dependabot PR, or for writing your own project's release notes.

### Objective checks passed

| Fixture | Baseline | Candidate |
|---|---|---|
| `closed-duplicate` | 15/18 | 15/18 |
| `closing-keywords` | 18/18 | 18/18 |
| `issue-hygiene` | 21/21 | 21/21 |
| `stamps-skip-quotes` | 12/15 | 14/15 |

Acceptance rule: the candidate passes at least as many checks as the baseline summed over every fixture, and no fixture loses more than 1. Decision: objective checks passed over all fixtures 66/72 -> 68/72; no worse in aggregate, and no fixture lost more than 1 check(s).

The patch is `/tmp/tmp.Dw3nX5y6o2/improvements/vendor-release-impact-issues/20261110T081218Z.patch`; apply it with `git apply` at the registry root.
