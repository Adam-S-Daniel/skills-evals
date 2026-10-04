# ADR 0005: The improvement loop reuses skill-creator's description loop and measures with this harness

- **Status:** proposed (2026-10-04). Built and tested with fakes only; no
  real run has been made.
- **Issues:** [#71](https://github.com/Adam-S-Daniel/skills-evals/issues/71)
  (the improvement loop; this is its smallest slice),
  [#232](https://github.com/Adam-S-Daniel/skills-evals/issues/232) (reuse
  Anthropic's skill-creator), and later
  [#122](https://github.com/Adam-S-Daniel/skills-evals/issues/122) (the same
  loop for guidance sections, which must extend this script, not fork it).
- **Deciders:** Adam, 2026-10-04: "I would like any pertinent built in or
  anthropic-published Claude skills or plugins related to evals to be
  leveraged where appropriate."

## Context

#71 asks for a loop that turns "the skill still fails check X" into a better
SKILL.md: propose an edit from the failing train fixtures, measure it on a
held-out fixture, and accept it only when validation held and train
improved. Anthropic publishes a plugin that already does half of that.
`skill-creator` (plugin `skill-creator@claude-plugins-official`, author
Anthropic, installed at user scope on the owner's machine; read at commit
`d182ca456ca09d31d139f7d3818d1d333b103cce`) ships, under
`skills/skill-creator/`:

| Path | What it does |
|---|---|
| `scripts/run_loop.py` | The description-optimization loop. Splits a `[{query, should_trigger}]` set 60/40 into train and held-out, stratified by `should_trigger` with a fixed seed (`split_eval_set`); evaluates the description on both; asks for a better one from the train failures only (held-out scores are stripped from what the proposer sees); repeats up to `--max-iterations`; returns JSON whose `best_description` is chosen by **held-out** score. |
| `scripts/run_eval.py` | The trigger measurement `run_loop.py` calls: plants the description as a project command file under the nearest `.claude/commands/`, runs `claude -p <query>` `--runs-per-query` times, and counts a trigger when the model reaches for that skill. |
| `scripts/improve_description.py` | The proposal step `run_loop.py` calls: one `claude -p` on stdin, with skill-creator's own guidance on writing descriptions and its 1024-character limit. |
| `scripts/aggregate_benchmark.py` | Mean/stddev and with-vs-without delta over its own `grading.json` runs. |
| `agents/grader.md`, `agents/comparator.md`, `agents/analyzer.md` | Subagent prompts that grade expectations against a transcript, compare two outputs blind, and explain the winner. |

The rest of #71 has no counterpart there. skill-creator grades behavior with
an LLM grader reading expectations (`agents/grader.md`); it has nothing
equivalent to `harness/scorers/objective.py`, which replays a workspace's
changeset and decides a check by its files, git state and command log rather
than by a model's reading of them. DESIGN.md's rule that decidable facts are
never pushed onto a judge applies here as it did to `claude plugin eval`
(DESIGN.md, "`claude plugin eval`"): the behavior half has to be measured by
this harness or it is not measured the way every other number here is.

## Decision

`scripts/propose_skill_edit.py <skill>` composes the two:

1. **Trigger half — skill-creator, unmodified.** The script runs
   `scripts/run_loop.py` from the installed plugin (found through
   `~/.claude/plugins/installed_plugins.json`, or `--skill-creator` /
   `$SKILL_CREATOR_DIR`) with its `scripts` package on `PYTHONPATH`, the
   same module its documented `python -m scripts.run_loop` runs. It is
   reached through a link planted in the scratch project so the script path
   is a literal the suite's fork scan can classify. It gets its documented
   arguments (`--max-iterations 5 --runs-per-query 3 --holdout 0.4`, browser
   report off). It keeps skill-creator's split, its held-out selection and its
   proposer; nothing of it is copied into this repo. Its working directory is
   a scratch project holding `.claude/settings.json`, so the command files
   it plants never land in a real checkout. Settings disable every local
   registry plugin providing the skill (see the hardening addendum). The
   query set is
   `--trigger-eval-set FILE` when given, else derived from fixtures: the
   train fixtures' prompts should trigger and every other skill's fixture
   prompts should not. **The validation fixture's prompt is always removed**,
   so the trigger loop never trains on the fixture that decides acceptance.
2. **Body half — one custom proposal call.** skill-creator has no step that
   edits a SKILL.md body from failed checks, so this is ours: one headless
   call to the committed roster's judge model, prompt on stdin, `--tools ""`,
   `--permission-mode default`, fed SKILL.md, the skill's `PURPOSE.md` when
   it has one, and each train fixture's failed checks with the tail of that
   trial's reply. It must answer `{rationale, unified_diff}`. The diff may
   name `SKILL.md` only and may not touch the frontmatter (the name is fixed;
   the description belongs to the trigger half). A diff that breaks either
   rule is recorded as `invalid-proposal` and nothing is measured.
3. **Measurement — this harness.** Two scratch registries are extracted from
   `git archive <ref>` of the local registry checkout; they carry no `.git`,
   so there is no remote and no push path in them. Baseline and candidate
   are each one `harness/run_eval.py evals/<skill> --arm with_skill
   --trials 3` against their scratch copy. `scripts/local_eval.py`
   ([PR #230](https://github.com/Adam-S-Daniel/skills-evals/pull/230), open)
   is deliberately not a dependency; see Consequences.
4. **Split and acceptance.** The skill needs at least three nested fixtures
   (else exit 2, "needs more fixtures"). In name order, validation is the
   fixture at `rotation % n`, where `rotation` defaults to the number of
   records already written for the skill, so consecutive runs hold out a
   different fixture, excluding an optional fixed `--holdout`. A candidate
   is **accepted** only when validation held
   (objective pass rate not lower; judge mean not lower by more than 0.5)
   **and** train met `--min-gain` (default .10 on the normalized 0..1 scale:
   objective pass rate, or judge mean divided by 10 when objective is equal).
   The fixed holdout must not regress on either score. Any errored or
   unscored fixture, or missing expected judge score, rejects as inconclusive.
5. **Output stays local.** `improvements/<skill>/<ts>.json` is written every
   time (rejections are the high-value record), `<ts>.patch` whenever a
   candidate existed (rooted at the registry, `git apply`-able), and
   `<ts>.pr-body.md` on accept. The default root is outside the repository
   (`$XDG_STATE_HOME/skills-evals`, else `~/.local/state/skills-evals`). The
   script opens no pull request, pushes nothing and holds no credential.
6. **A local exhibit.** It runs under the operator's own login, so under
   [ADR 0002](0002-runs-bill-the-api-org-not-the-subscription.md) decision 4
   its numbers are not badge input, and it never runs in CI. There is no
   workflow: #71 says scheduling waits for three merged human-reviewed pull
   requests from it, and dispatch waits for the same evidence.
7. **Every model call goes through one injectable `Runner`** (`run_eval`,
   `run_description_loop`, `propose`), so `test/issues/test_issue_71.py` runs
   the whole pipeline offline with a fake, and `--dry-run` prints the plan
   (split, models, call counts) with no model call and no write.

### What was considered and not used

| skill-creator part | Why not |
|---|---|
| `agents/grader.md` | An LLM grader of expectations. The behavior half is scored by `scorers/objective.py` and this harness's judge, which already run with N trials. |
| `scripts/aggregate_benchmark.py` | Reads skill-creator's `grading.json` layout. `run_eval.aggregate_trials` already aggregates this harness's trials, and the decision reads that. |
| `agents/comparator.md` / `analyzer.md` | Blind A/B needs subagents and a reader; a candidate here is accepted on numbers, and the record carries both tables for the human reviewing it. |
| skill-creator's own query-writing step (a reviewed ~20-query set) | Not automated. The fixture-derived default is thin (two or more positives, other skills' prompts as negatives, few of them near-misses); a reviewed set can be passed with `--trigger-eval-set`. |

### Alternatives considered

| Alternative | Verdict |
|---|---|
| Reimplement the description loop here | Rejected: it would drift from Anthropic's, and the owner asked for the published tool to be used. |
| Let skill-creator measure the body edit too | Rejected: no objective scorer (see Context). |
| `claude plugin eval` for the trigger half | Not now: [#232](https://github.com/Adam-S-Daniel/skills-evals/issues/232) measured one run; it has a `tool_used: Skill` grader but no held-out description search. |
| One candidate per half, measured separately | Deferred: it doubles the paid measurement. The record says which halves changed, so a rejected combined candidate can be split by hand. |

## Consequences

- The number of model calls is bounded and visible before it starts (`--dry-run`
  prints it): 2 × fixtures × trials agent calls (plus as many judge calls),
  at most `5 × 3 × queries + 8` skill-creator calls, and one proposal call.
  There is no implemented per-skill spend cap or budget configuration file;
  the dollar cost is not bounded by these call counts. A spend-cap guardrail
  remains part of [#71](https://github.com/Adam-S-Daniel/skills-evals/issues/71).
- Only two skills qualify today: `writing-adrs` (three fixtures) and
  `adam-writing-style` (three, but its pairwise judge mode is refused by
  `run_eval.py`, so it needs `--no-judge`).
- The trigger split and the fixture split are independent: skill-creator
  holds out 40% of its query set with its own seed; this script holds out a
  fixture. Removing the validation prompt from the query set is what keeps
  the two from leaking into each other.
- **Convergence with PR #230.** `local_eval.py` adds the guards a local run
  should have (refusing `ANTHROPIC_*` and other credential variables, an
  allow-listed child environment, a results directory outside every work
  tree, a contamination probe). This script calls `run_eval.py` directly
  and has none of them. When #230 merges, `Runner.run_eval` should run
  through `local_eval.py` (or its guard functions) instead, so the loop
  inherits them; the record and decision code do not change.
- Not done here, from #71: the registry pull request itself, the
  `docs/skill-impact.md` entry, `improve.yml`, the idempotency check on an
  open `eval-improve/<skill>` branch, the budget refusal, and publishing
  records to `persistent/eval-results`.
- skill-creator's trigger runs retain the operator's real login. Scratch
  project settings disable the local registry plugins providing the target
  skill so those installed copies do not compete with the planted command.
  Federated marketplace sources are not fetched; their providers cannot be
  inferred from this registry archive.
- skill-creator is an external dependency read from the operator's plugin
  install. A plugin update can change `run_loop.py`'s output shape; the
  contract test in `test/issues/test_issue_71.py` runs the installed copy
  with a stand-in `claude` and fails if it does, but it is skipped wherever
  the plugin is not installed, CI included.

## Pre-real-run hardening addendum (2026-10-04)

The review of [PR #236](https://github.com/Adam-S-Daniel/skills-evals/pull/236)
identified five requirements before any real run. The implementation still
has only offline test evidence; no real evaluation was run for this change.

- **Trigger isolation uses project configuration.** The archived registry's
  `.claude-plugin/marketplace.json` supplies the marketplace and entry names
  for `enabledPlugins` keys. Local plugin manifests and marketplace entries
  supply additive skill directories, beside default `skills/`; an explicit
  skills list for a marketplace-root plugin limits that default scan. A
  plugin manifest is optional. Paths stay inside their archive and plugin
  roots, malformed manifests refuse the run, and remote sources are skipped.
  This follows the [plugin manifest reference](https://code.claude.com/docs/en/plugins-reference).
  Each provider is set to `false` in the scratch project's settings before
  the trigger loop starts. The run keeps the operator's login through the
  real `HOME`; a throwaway `HOME` belongs only to offline tests.
- **Acceptance requires material gain.** `--min-gain` must be finite and
  greater than zero, at most one; its default .10 means ten percentage points
  of objective pass rate, or one judge point on the 0..10 scale when the
  objective rate is exactly equal. The boundary is inclusive (with only
  1e-12 absolute tolerance for floating-point subtraction), neutral edits
  reject, and judge gains cannot rescue an insufficient objective gain.
  This conservative default reduces acceptance of tiny movements; it is an
  empirical heuristic, not calibrated statistical significance. The rotating
  validation judge tolerance remains .5, also uncalibrated, as requested in
  [#71](https://github.com/Adam-S-Daniel/skills-evals/issues/71).
- **A fixed holdout protects against rotation leakage.** `--holdout` names
  one nested fixture excluded from training and the rotating validation
  population on every run. Three total fixtures still suffice: one train,
  one rotating validation, one fixed holdout. Both harness runs measure it,
  and objective rate and judge mean must not regress (zero judge tolerance).
  Its prompt is removed from every trigger query set, including overrides;
  its prompt and failure evidence never enter the body proposal. Missing or
  errored measurements reject as inconclusive. Choose a fixed fixture with
  a prompt distinct from every train fixture, select a previously untrained
  fixture, and keep the same `--holdout`
  on subsequent runs; a duplicate train prompt refuses before calls or
  writes. If a train prompt duplicates
  validation's prompt, exclusion can remove all positive trigger queries;
  that case refuses and requires a reviewed `--trigger-eval-set`, rather than
  leaking the validation prompt. `writing-adrs`' bootstrap and
  existing-convention fixtures currently share that prompt.
- **Bad descriptions reject without crashing.** Control characters,
  including DEL and C1 controls, or an unrenderable YAML description produce
  the ordinary `invalid-proposal` record and no candidate measurement.
- **Dry-run preflight is executable.** Every fixture's model selection uses
  the actual `--no-judge` flag. Unsupported judge modes or unavailable judge
  models refuse before calls or output writes and name `--no-judge` as the
  corrective option. The deferred spend cap is a documentation fact, not a
  mechanism this change implements: no script reads a budget file, and the
  plan reports call bounds rather than a dollar ceiling.
