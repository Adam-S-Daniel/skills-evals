## Proposed `writing-adrs` SKILL.md edit (validation-gated)

Produced by skills-evals `scripts/propose_skill_edit.py --trim-description` ([#687](https://github.com/Adam-S-Daniel/skills-evals/issues/687)): the description was over adam-agentskills' 400-character listing cap, so its `length-limit` waiver is removed here too. Only the description changed; the body is unchanged. A local exhibit (skills-evals ADR 0002, decision 4), not badge input.

- Registry: `adam-agentskills` at `0370ab7ea012d00015ff2590349450404f019d88`
- Length: 572 -> 395 characters
- Measured: every fixture, 3 trial(s) each, `with_skill` arm on `claude-sonnet-5-5`, no judge; proposal model `claude-fable-5-2`

### Description

Before: Write a lightweight Nygard-style Architecture Decision Record under `docs/decisions/` when a non-obvious decision needs context that won't fit in a code comment and would rot if left only in a PR description. Trigger when the user asks "should I document this", "add an ADR", "why did we do X" referring to a past choice with no comment trail, or when you find yourself drafting a multi-paragraph PR description justifying a one-line change. Also covers the bootstrap case (creating `docs/decisions/README.md` + the first ADR from scratch) if the folder doesn't exist yet.

After: Write a Nygard-style Architecture Decision Record in docs/decisions/ for a non-obvious decision whose context won't fit a code comment and would rot in a PR description. For "should I document this", "add an ADR", "why did we do X" about a past choice with no comment trail, or a multi-paragraph PR description justifying a one-line change. Bootstraps the folder (README + first ADR) if missing.

### Objective checks passed

| Fixture | Baseline | Candidate |
|---|---|---|
| `bootstrap` | 27/27 | 27/27 |
| `existing-convention` | 21/21 | 21/21 |
| `pr-body-outgrows-itself` | 14/39 | 14/39 |
| `supersede` | 39/39 | 39/39 |
| `why-no-comment-trail` | 30/33 | 30/33 |

Acceptance rule: the candidate passes at least as many checks as the baseline summed over every fixture, and no fixture loses more than 1. Decision: objective checks passed over all fixtures 131/159 -> 131/159; no worse in aggregate, and no fixture lost more than 1 check(s).

The patch is `/tmp/tmp.GpFrtBX3yv/improvements/writing-adrs/20261117T183624Z.patch`; apply it with `git apply` at the registry root.
