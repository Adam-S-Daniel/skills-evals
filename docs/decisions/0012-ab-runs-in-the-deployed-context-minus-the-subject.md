# ADR 0012: An A/B runs both arms in the context the subject deploys into, and removes only the subject

- **Status:** accepted (2026-10-07). Nothing is built yet.
- **Issue:** none; raised in review of the first scaffolded real-work fixture
  ([#329](https://github.com/Adam-S-Daniel/skills-evals/pull/329)).
- **Decider:** Adam (2026-10-07), approving the proposal as described:
  "Create the ADR. I already approve it based on your description".

## Context

An A/B is meant to measure one subject: one skill or one guidance section.
What the two arms carry besides the subject decides what that measurement
means.

- **Skills are measured in isolation.** [`DESIGN.md`](../../DESIGN.md)
  "Purpose" asks "does installing this skill actually improve agent
  behavior?" The `with_skill` arm installs the one skill. The
  `without_skill` arm installs nothing. Neither arm carries the other skills
  or the fleet guidance: arms run with `--setting-sources project`, and a
  real-work seed has its fleet context stripped (`strip_agent_context:`).
  A seed keeps its repository's own `## Repo-specific additions` (Q5), and
  the CLI's bundled skills stay available in both arms.
- **Guidance already names the right question, but defaults to the other
  one.** "Guidance subject" says a section stays only if "the full guidance
  WITH it beat[s] the full guidance WITHOUT it". Even so, the default pair is
  `section`/`none`. The in-place pair `full`/`full-minus-section` runs only
  when a fixture declares `ablation:` and the run passes `--ablation`, or
  when a fixture's explicit `arms:` selects it (`harness/guidance.py:79`).
- **Neither kind of arm carries the other kind of subject.** Skill arms get
  no guidance, and guidance arms get no skills.

A skill or section deploys into a session that already holds the rest of the
fleet's context: the guidance (base plus the repository's opt-in sections)
and every skill the repository adopts through its `skills.lock`. An isolation
pair cannot see the effects that decide whether a subject is worth keeping
there:

- **Overlap.** When another skill or section already teaches the behavior,
  the subject's marginal value is near zero, but an isolation pair credits
  the subject with all of it.
- **Triggering.** A skill has to be chosen from the 16 to 35 skills a
  session loads ("Guidance subject"), each competing on its description. An
  isolation pair has nothing to choose between.
- **Context cost and interference.** The guidance corpus is tens of
  kilobytes: `agents-md/base.md` alone was 24,962 bytes on 2026-10-07, and
  the delivered size, with a repository's opt-in sections, still has to be
  measured.
  Whether a subject still works inside it, or crowds something else out, is
  what `full-minus-section` exists to measure.
- **Confounded model mix.** The fleet guidance tells agents to delegate to
  subagents on cheaper models. A guidance arm that carries that rule against
  a baseline that does not partly measures a different model mix, not the
  section.

## Decision

1. **The default A/B for every subject is in place.** Both arms carry the
   same deployed context. The `with` arm adds the subject, and the `without`
   arm leaves it out. Nothing else differs between them.
   - If the subject is part of the context, the `without` arm removes it
     (leave one out).
   - If it is not, the `with` arm adds it.
2. **The deployed context is what a named repository loads.** It consists of:
   - that repository's adopted skill bundles, from its `skills.lock`;
   - the fleet guidance it receives (base plus its opt-in sections).

   Both are resolved at a recorded digest and delivered byte-identically to
   both arms. A real-work fixture defaults to its source repository. Any
   other fixture names a repository.
3. **Isolation pairs stay, as an opt-in diagnostic.** These are `skill`/none
   and `section`/`none`. They answer "does this subject teach the behavior at
   all": cheaper, with less variance, and useful while writing or improving a
   subject. Their results are reported apart from in-place results, never
   mixed in.
4. **`strip_agent_context:` still runs.** It removes the seed's own copy of
   the fleet context, which is stale and unverified. The harness then
   delivers the deployed context itself, and each arm proves what it got
   (see "Implementation requirements": the existing guard and decoy are not
   enough).
5. **Each summary records the context:** the repository it came from, the
   bundles and digests, the guidance bytes, and whether the subject was
   removed from the context or added to it.

## Implementation requirements

An independent review of this record (Codex, `gpt-6.1-sol`, 2026-10-07)
found that the existing mechanisms do not deliver decision 1 as they stand.
The build must cover each of these:

- **A guard that proves leave-one-out.** Decoys are minted only for `mode:
  none` (`harness/run_eval.py`, around `_mint_decoy`). `full` and
  `full-minus-section` get the same treatment token and no distinct
  forbidden token, so an arm that wrongly received `full` would pass both
  guards. No guard checks a skill catalog or digest either. Each in-place
  arm needs its own proof: the subject's marker must be present in the
  `with` arm and absent from the `without` arm. That covers sections and
  skills alike, by content digest, including plugin-qualified copies.
- **Local authentication.** The guidance path's scratch `HOME` and
  `CLAUDE_CONFIG_DIR` lose the interactive `/login` (`DESIGN.md`, "Guidance
  subject"). Moving skill arms onto it breaks local subscription runs unless
  authentication is resolved explicitly. Using the real user configuration
  instead would bring back ambient context and trusted sandbox grants. The
  ADR 0011 `--settings` flags must survive either way.
- **An arm lifecycle and names.** `without_*` arm names must carry `none`
  today, so a `full-minus-section` baseline is a configuration error.
  Installing an adopted context that already holds the tested skill before
  the `with_skill` install raises `FileExistsError`. Restoring `.claude` or
  `skills.lock` before `seed_guard` fails the strip check. The order is:
  strip, guard, deliver the context, then add or remove the subject.
- **A context resolver.** `guidance.corpus()` returns base plus at most the
  subject's own opt-in file, not every section a repository adopts.
  Scaffolded seeds discard `skills.lock` and record their source repository
  and revision only as comments. A lock can name further registries, each
  with its own revision and layout. The resolver needs structured fixture
  metadata (repository, revision) and must resolve the lock and sections as
  of that revision, not today's `main`.
- **Cost accounting.** Guards make their own model calls, and their usage is
  discarded today. Running full-context guards on every skill arm adds
  usage the totals don't show. Summaries should report agent tokens (the
  efficiency KPI) separately from total evaluation cost, guards included.
  The fixture schema needs a context-size budget.

## Consequences

- **Deltas mean what the keep-or-remove decision needs:** the subject's
  marginal value where it actually runs. Redundant subjects show small or
  negative deltas, which is a finding, not noise.
- **Smaller deltas need more trials.** Every arm also carries the full
  context, so per-trial tokens and subscription usage rise. The token KPI
  (Q7) compares like with like, because both arms pay for the same context.
- **Skill arms change delivery.** Delivering guidance requires the guidance
  path (`--setting-sources user,project`, a scratch `CLAUDE_CONFIG_DIR`, and
  the guard). It no longer applies only to guidance arms.
- **Fixtures need a context.** A fixture without a source repository must
  name one, and existing skill fixtures need a migration.
- **Results stop being comparable across the switch.** In-place deltas are
  not comparable with the isolation deltas recorded so far, so the
  regression history restarts at the switch, and summaries say which pair
  produced them.
- **Network and filesystem isolation are unchanged.** The arms' isolation
  ([ADR 0011](0011-sandbox-agent-arm-network.md), once merged) applies to
  both arms alike.

## Alternatives considered

- **Keep isolation as the default.** Rejected: it credits a subject with
  behavior the rest of the context already provides, and it never tests
  triggering or interference. It stays available as the diagnostic in
  decision 3.
- **Use the whole registry as the context instead of one repository's
  adopted set.** Rejected: adoption is opt-in per repository (a repository
  can stay out on purpose to save context), so the whole registry is not
  what any session loads, and it would measure a context nobody runs.
- **Run both pairs on every fixture.** Rejected as the default: it doubles
  the usage for a diagnostic that matters only while a subject is being
  built.
- **Keep the in-place pair opt-in for guidance (`ablation:`) and add the
  same opt-in for skills.** Rejected: opt-in leaves the default answering
  the less useful question, which is how guidance has worked so far.

## References

- [`DESIGN.md`](../../DESIGN.md): "Purpose", "Guidance subject", and
  "Real-work fixture decisions (Adam, 2026-10-06)" (Q5, Q7).
- `harness/guidance.py`: the delivery modes, including `full-minus-section`.
- [ADR 0010](0010-run-ai-eval-steps-in-a-routine-fired-by-actions.md):
  real-work measurement and routine runs.
