# ADR 0010: Run the AI steps of skill and guidance evals in a routine fired by Actions, and measure agent effectiveness on real work

- **Status:** proposed (2026-10-06). Nothing is built; the open decisions
  below are Adam's.
- **Issues:** [#71](https://github.com/Adam-S-Daniel/skills-evals/issues/71)
  (the improvement loop),
  [#122](https://github.com/Adam-S-Daniel/skills-evals/issues/122) (the same
  loop for guidance sections).
- **Decider:** Adam (pending).

## Context

Adam, 2026-10-06, on the note that guidance evals were "blocked on the paid
CI path":

> "“blocked on the paid CI path for guidance evals”: use Claude routines to
> avoid having to pay API cost"

> "The skills improvement loop should not only use skill-creator. Both skills
> and guidance should be evaluated for how they improve agents’ efficiency and
> effectiveness at doing the work I want them to do. Can the AI steps in occur
> via GitHub actions calling claude routine API triggers?"

**What routines offer** ([Routines](https://code.claude.com/docs/en/routines),
[Trigger a routine via API](https://platform.claude.com/docs/en/api/claude-code/routines-fire),
read 2026-10-06; research preview, beta header
`experimental-cc-routine-2026-04-01`):

- Triggers: schedule, API, GitHub events. The API trigger is
  `POST https://api.anthropic.com/v1/claude_code/routines/{routine_id}/fire`
  with a per-routine bearer generated only in the web UI, scoped to firing
  that one routine, shown once, regenerable and revocable.
- An optional free-text `text` (at most 65,536 characters) is delivered
  wrapped in a `<routine-fire-payload>` block labeled untrusted; the
  routine's saved prompt must opt in to acting on it. JSON arrives as a
  literal string.
- The response carries `claude_code_session_id` and
  `claude_code_session_url`. There is no polling or status API; a green run
  status means only that the session exited without an infrastructure error.
- Runs "draw down subscription usage the same way interactive sessions do",
  not API billing (metered overage only if usage credits are on). Hourly
  limits: 30 fires per routine (shared with Run now), 100 API fires per
  account, 100 scheduled runs per account.
- Runs push `claude/`-prefixed branches unless the prompt directs otherwise,
  can open PRs, and act as Adam's GitHub identity. No permission-mode
  picker: the session runs shell commands without approval.
- Nested `claude -p` inside a cloud session works: _agent-guidance's
  prompt-audit sweep runs a nested `/doctor prompt-audit` and logs its auth
  probe as `firstParty oauth_token` with "billing basis unverified"
  ([`docs/reference/prompt-audit-runs.md`:24-26](https://github.com/Adam-S-Daniel/_agent-guidance/blob/35f62ec4d9ab7fd8b9d9fe2e3a547c7d5926c3f9/docs/reference/prompt-audit-runs.md#L24-L26),
  [`docs/routines/prompt-audit-sweep.md`:261-268](https://github.com/Adam-S-Daniel/_agent-guidance/blob/35f62ec4d9ab7fd8b9d9fe2e3a547c7d5926c3f9/docs/routines/prompt-audit-sweep.md#L261-L268)).
  How a nested run authenticates inside a routine is not documented.

**What this repo does today, and what blocks the routine path:**

- [ADR 0002](0002-runs-bill-the-api-org-not-the-subscription.md) decision 1
  (lines 82-85): arms never run on a subscription credential in CI, because a
  `bypassPermissions` arm running registry content must not reach one. Its
  alternatives table (line 115) records a routine fired from `eval.yml` as
  permitted but outside the `main`-pinned WIF trust model; decision 4
  (lines 101-108) makes locally produced results "a local exhibit, not badge
  input".
- `scripts/local_eval_guard.py:23` refuses `CLAUDE_CODE_OAUTH_TOKEN` and
  `CLAUDE_CONFIG_DIR` in the environment; `harness/guidance.py:780-801`
  (`agent_env`) builds an arm's environment from an allowlist (lines
  150-155) that passes `ANTHROPIC_*` and drops every ambient `CLAUDE_*`.
- [ADR 0005](0005-improvement-loop-reuses-skill-creator.md) measures the
  loop with this harness but proposes through skill-creator's description
  loop; its serial trigger-eval addendum (line 306) merged in
  [PR #296](https://github.com/Adam-S-Daniel/skills-evals/pull/296).
- The only guidance fixture, `evals/guidance/_delivery/fixture.yaml`, is a
  delivery canary, "not a behavioral A/B" (lines 1-5). Only `writing-adrs`
  (4 fixtures) and `adam-writing-style` (3) have the three fixtures a
  train/held-out split needs.
- #71 item 5: the improvement workflow is not scheduled "until three
  human-reviewed PRs from it have merged".

## Decision (proposed)

1. **GitHub Actions owns scheduling, bookkeeping and ingestion; a routine
   owns the AI steps.** A workflow builds a JSON task spec (run id, roster
   ref, fixture list, arms, trial count, base sha) and fires one routine via
   the API trigger with the spec as `text`. The routine's saved prompt
   checks out the named sha, runs the eval arms, the judge and (for the
   loop) the proposer, and pushes results to `claude/eval-<run id>`. It
   never writes `persistent/eval-results` or `main`.
2. **Results are untrusted input to Actions.** A workflow on push to
   `claude/eval-*` validates the result files against a schema (run id
   matches a fire it recorded, paths confined, sizes bounded, no executable
   content), then ingests them into `persistent/eval-results`. A missing
   push within a deadline marks the run failed; there is no polling API to
   ask instead.
3. **Measure agent effectiveness on real work, not only triggering.**
   Fixtures are drawn from what Adam's agents actually do (writer, reviewer
   and CI-debug tasks from his sprints), scored on task success plus
   efficiency: turns, usage (tokens), wall time and review rounds. The same
   A/B harness runs skills (with/without the skill) and guidance
   (with/without the section). skill-creator stays one proposer among
   others, not the loop's definition.

## Open decisions for Adam

1. **ADR 0002 decision 1.** A routine's nested arms run on the account's
   subscription credential, which decision 1 forbids for arms. Options:
   supersede it for routine runs; or run arms as the routine's own
   subagents instead of nested `claude -p` (no extra credential in reach,
   but weaker isolation than `agent_env` and a different measurement);
   or keep arms on the API path and move only the judge and proposer.
2. **Usage-terms comfort at scale.** Routines are a documented automation
   surface, but an eval matrix is many runs per week on one personal
   subscription; ADR 0002 read the Consumer Terms for this.
3. **Badge input or local exhibit.** Do routine results feed the badge, or
   stay an exhibit as ADR 0002 decision 4 treats non-`main`-pinned runs?
4. **#71's three-PR gate.** Keep it before any scheduled loop, or replace
   it for routine-fired runs.
5. **Where the fire bearer lives.** A repo or environment secret; its name
   must avoid the gitleaks keyword list (`key`, `token`, `secret`, `auth`
   and the rest) wherever it is serialized beside a value in a generated
   file.

## Consequences

- Guidance and loop runs stop competing for API dollars; they compete for
  subscription usage and the hourly fire caps instead.
- The trust model splits: WIF runs remain `main`-pinned; routine runs are
  attested only by the validator, so their numbers are not comparable to
  API-path numbers until a paired run shows they agree.
- The research-preview API can change shape; the firing step pins the beta
  header and fails closed on an unknown response.
- Real-work fixtures cost more to write and to score than trigger queries,
  and need objective checks first, per DESIGN.md's rule that decidable
  facts never go to a judge.

## Smallest next PRs

1. **Probe, no code change:** a routine created in the web UI, fired once by
   hand with a toy spec, records `claude --version`, the nested auth probe
   and whether a nested `claude -p` under an `agent_env`-shaped environment
   runs, then pushes `claude/eval-probe-<id>`.
2. A dispatch-only workflow that fires the routine and records the session
   URL, behind the decisions above.
3. The `claude/eval-*` validator and ingester, tested with fakes.
4. Two real-work fixtures (one writer, one CI-debug) with objective checks.

## Alternatives considered

- **Stay on the API path** (ADR 0002): keeps the trust model, keeps the
  cost that blocks guidance evals.
- **Routine pushes straight to `persistent/eval-results`:** removes the
  validation step that treats model-written output as untrusted.
- **`setup-token` in `eval.yml`:** rejected by ADR 0002's table; a routine
  at least keeps the credential out of the Actions runner.
