# ADR 0007: Run ready fixtures on the weekly schedule

- **Status:** proposed (2026-10-04)
- **Issue:** [#68](https://github.com/Adam-S-Daniel/skills-evals/issues/68), partially implemented.
- **Deciders:** the owner requested that scheduled runs include additional ready evals; this package fixes the initial four entries.

## Context

[The real-eval workflow](../../.github/workflows/eval.yml) schedules one
fixture because a schedule has no dispatch input and selection falls back
to `evals/workflow-path-audit`. Three more fixtures have local qualification
evidence. Automatically discovering every fixture would also run unfinished
or unqualified work, and readiness must remain an explicit reviewed decision.

The workflow runs committed fixture content with a short-lived, spend-capped
federated bearer. Each agent runner has read-only repository access and its
own credential exchange. Publishing requires a separate fresh runner with
write access. [ADR 0004](0004-eval-runs-on-the-roster-its-run-merged.md)
requires the roster update and confirmed disarm to finish before any eval.
GitHub matrix job outputs do not provide a reliable per-fixture result map,
and simultaneous publishers would compete for the same results branch.

## Decision

1. Commit `evals/scheduled.yml` as a nonempty `fixtures` list. Each entry has
   exactly `path` and a nonempty, single-line `readiness` note. The initial
   entries are `evals/workflow-path-audit`, `evals/embeddable-tool-pages`,
   `evals/review-bash-ci-reliability`, and
   `evals/skills-doctor/bucketed-account-store`. Preserve the supplied local
   evidence without inventing a measurement date or claiming a paid CI run.
2. A read-only planning job reads the schedule list only for `schedule`.
   `workflow_dispatch` still reads `fixture` from `GITHUB_EVENT_PATH`, with
   today's single-fixture default and unchanged `roster_only` behavior.
   Reject malformed schemas, duplicate entries, invalid path characters,
   and paths outside the committed fixture set before emitting the matrix.
3. Run one eval matrix leg per fixture, `fail-fast: false`, `max-parallel: 2`.
   Each leg selects and validates again before its own OIDC exchange, uses
   its own runner and temporary files, and uploads a uniquely named artifact.
   The fixture-relative path remains its distinct `eval_key`; numeric matrix
   slots identify artifacts without flattening nested fixture paths.
4. Keep roster, disarm, roster-pr, and roster-wait as single jobs per run.
   Every eval and publisher retains ADR 0004's confirmed-clear gate and the
   same permissions and credential sources. No agent runner receives a write
   credential; no token is passed between matrix legs.
5. Match publishing legs to the planned matrix and serialize them with
   `max-parallel: 1`, `fail-fast: false`. Each publisher has a fresh checkout,
   validates its fixture/key independently, downloads only its matching
   successful payload, and builds that fixture's badge against accumulated
   history before its commit. Failed evals keep diagnostic artifacts but
   cannot publish partial results; their missing success payload is reported.
   An aggregate matrix failure must not suppress successful sibling publishes.
   Retain workflow concurrency `real-eval`, `cancel-in-progress: false`, so
   separate runs cannot compete with these serialized publishers.
   Nested skill badges read `results/<skill>/<timestamp>/<fixture>/`, the
   harness's existing layout, and include only that fixture's pairs in their
   window; flat skill and guidance badges retain their existing layouts.
6. Retain the per-fixture harness budgets and the existing guidance-fixture
   timeout check; also check every scheduled fixture against the eval job's
   timeout, including setup, agent, and judging costs with defaults.

## Consequences

The weekly schedule exercises exactly the reviewed list, and adding an entry
is a visible spend decision. The workflow's existing estimate is about
$0.30–0.90 per skill fixture: four fixtures imply about $1.20–3.60 per
scheduled run, or $6–18 for five weekly runs. These are estimates rather than
a cap; model choice, judging, and actual usage affect cost. The API workspace
spend limit remains the hard ceiling. Readiness evidence does not require a
positive objective delta: the account-store fixture qualifies with a stronger
judge score even though its supplied objective average is lower.

Successful siblings publish despite an errored eval. Publishing is serialized
and therefore adds runner time; a missing or unavailable payload is reported
and never substituted with another fixture's output. Dispatch remains one
fixture and gains no bulk input. Fixtures are admitted only through committed
paths, not through results-branch content or an API response.

This implements the owner-requested ready list, not all of #68: rotation,
monthly sweeps, model products, trial changes, budget enforcement, and a
published aggregate index remain outside this package. Scheduled local
qualification evidence is not substituted for CI badge input.

## Alternatives considered

- Discover all `fixture.yaml` files: rejected because existence is not readiness.
- Put four paths directly in workflow YAML: rejected because readiness evidence
  and additions belong in a small reviewed list with a validated schema.
- Reuse a matrix job's final `eval_key` output: rejected because completion
  order can select a sibling's key and mislabel published results.
- Publish concurrently or from the eval runner: rejected because the former
  races the results branch and the latter exposes write auth to agent code.
- One batch publisher gated on aggregate eval success: rejected because one
  failed fixture would discard all successful siblings' results.

## References

- [Matrix runner issue](https://github.com/Adam-S-Daniel/skills-evals/issues/68).
- [Workflow security contract](../../.github/workflows/eval.yml).
- [Reviewed schedule](../../evals/scheduled.yml) and
  [planner and admission checks](../../scripts/plan_scheduled_evals.py).
- [Shared matrix and artifact pattern](https://docs.github.com/en/actions/how-tos/write-workflows/choose-what-workflows-do/run-job-variations#using-an-output-to-define-two-matrices):
  GitHub's documented producer and consumer matrix pattern.
- [Design and budget](../../DESIGN.md).
- [Decision index](README.md).
