# ADR 0012: An A/B runs both arms in the context the subject deploys into, and removes only the subject

- **Status:** accepted (2026-10-07). Status note (2026-11-03): built. In-place
  fixtures (a top-level `context:` mapping) are loaded by `harness/context.py`
  and run through the routine, and the addenda below describe what was added
  since.
- **Amended 2026-11-02:** keep-or-remove runs test main's copy of a skill
  subject (see "Addendum: main's copy").
- **Amended 2026-11-02:** arms that stand for the real setup run the fleet
  hooks the context deployed (see "Addendum: fleet hooks are part of the
  deployed context").
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

## Decisions on the build (Adam, 2026-10-07)

An implementation plan (Codex, `gpt-6.1-sol`, 2026-10-07) raised five
questions for the owner. Answers, recorded verbatim:

- **Local runs:** "Cloud-only for now (Recommended)". In-place runs are
  built for the routine path, where a nested `claude` authenticates with no
  credential in reach (ADR 0010). A local in-place run fails closed with a
  named error. A credential-file adapter for local runs is deferred to its
  own review and a controlled live test.
- **Context repository:** "Explicit per fixture (Recommended)". Every
  fixture names its context repository: the operational repository the
  skill is for, or a representative consumer. There is no fleet-wide
  default. A fixture without one can run only the isolation diagnostic.
  Real-work fixtures take theirs from the scaffolder's candidate
  (repository and base commit).
- **Guidance revision:** "Pin explicitly, else block (Recommended)". A
  fixture's `guidance_revision` must be one whose bytes match the managed
  guidance the repository shipped at that commit. If none can be proven,
  the fixture is blocked from in-place runs. "The latest guidance at that
  time" is never inferred.
- **Subject version:** "Deployed by default (Recommended)". Keep-or-remove
  evaluations test the version the context repository deployed. The
  improvement loop explicitly supplies its candidate, which replaces only
  that subject in the `with` arm. Both digests are recorded.
- **Context budgets:** the plan's default stands. Measure the migrated
  contexts, commit limits with about 25% headroom, and require review to
  raise them. A context over budget blocks the run rather than being
  truncated.

## Bare baseline addendum (Adam, 2026-10-27)

Ablation, the in-place pair of decision 1, stays the main approach. Next to
it, each fixture that runs in place (its `fixture.yaml` has a top-level
`context` mapping) gets one **bare** run per model: a single arm with
nothing of ours loaded, no skills, no guidance and no memory. It is the
isolation `without_skill` arm (`harness/run_eval.py --pairing isolation
--arm without_skill`); `strip_agent_context:` still runs. Its result is
compared with the same fixture's in-place `with` arm on the same model, which
says how much the whole deployed context adds over the model alone.

How often: Adam first chose monthly, then changed it to "one time per model
per version of model". A fixture gets a bare run for a model id (for
example `claude-sonnet-5-5`) once, and again only when a new model id
appears among the arms of `evals/roster.yml`. Nothing repeats on a clock.

How it is built:

- `routine-eval-fire.yml` takes `arms: bare` in eval mode, for an in-place
  fixture only (a fixture without a `context` mapping already has a bare
  arm: its isolation `without`). The run's title reads
  `Fire eval routine: eval bare <fixture> <model>`.
- `scripts/plan_week.py` plans one bare fire of three trials per (scheduled
  in-place fixture, roster model) that has none yet, in a last band with no
  minimum share, so it spends only room the other bands leave. A bare run
  ingested for the cell, or a bare fire that succeeded or is still running,
  counts as done; a refused or failed fire does not.
- Decision 3 applies: a bare run is an isolation result, reported apart and
  never pooled. `scripts/compute_gates.py` sets it apart (a `without` arm
  without `pairing: in_place`, with no `with` arm beside it, on an in-place
  fixture) and lists it under `bare_runs`; no cell, verdict, improve
  evidence or cost ratio reads it.
- A bare fire is one run to the weekly allowance guard, as any eval fire is.
  The weekly plan reserves it as one arm: its cell's mean cost per arm
  trial, times its three trials.

## Addendum: main's copy (Adam, 2026-11-02)

Decision (Adam, 2026-11-02, option 1 of the design later filed as skills-evals#548): keep-or-remove runs test main's copy of the subject skill, not the copy the context repository deployed; the without arm still has the subject removed.

The decision was recorded in the design log the day #548 was filed; the
build is [skills-evals#559](https://github.com/Adam-S-Daniel/skills-evals/issues/559),
on the shared resolver `run_eval.main_copy` and the summary keys
`subject_source` and `subject_revision` that
[#560](https://github.com/Adam-S-Daniel/skills-evals/pull/560) added.

### Consequences of the build

- **Skill subjects only.** This replaces the 2026-10-07 "Subject version:
  Deployed by default" answer above for skill subjects only; guidance
  subjects still test the deployed section, and `--subject-candidate` still
  replaces the subject. That answer stays as recorded.
- **cms-platform skills are measured at cms-platform main.** A skill from
  the cms-platform registry is tested as it stands on cms-platform main,
  which consumer sites get once a cms-platform release containing it ships
  and they bump to it. Verdicts are about text that will ship, ahead of the
  release a site runs today. Settled from the decision on 2026-11-02 (the
  #559 comment).
- **A skill edit pauses pooling.** compute_gates digests main's copy when the
  gates run, and a run records main's copy when it fired. After a skill edit
  on main neither arm pools (the without arm pairs with a current with group)
  until a new with run lands.
- **The refusals.** Each is a named configuration error before any paid
  call, checked in this order: `invalid_registry_field` (a fixture
  `registry:` that is not a URL string); `resolve_skill_subject`'s own;
  `registry_mismatch` (an adopted subject whose fixture `registry:` is not
  the registry the context deploys it from); `main_copy`'s
  (`registry_unknown`, `registry_checkout_missing`, `main_copy_missing`
  when the skill moved to another registry, `main_copy_ambiguous`);
  `main_bundle_mismatch` (main's copy is in another bundle);
  `unsafe_path`; `main_copy_mismatch` (an added subject whose resolved copy
  is not main's); `registry_checkout_unversioned` (the registry checkout is
  not the top level of its own Git repository, or has no HEAD);
  `registry_checkout_dirty` (the skill directory differs from HEAD in a
  path, a mode or a byte, or HEAD holds something other than a regular
  file there); `registry_checkout_not_main`; the catalog and
  `candidate_identity_mismatch` checks on main's copy; `budget_exceeded`.
- **`subject_source: main` means the checkout's HEAD.** It is checked against
  `refs/remotes/origin/main` when that ref exists and refused when they
  differ; without the ref, HEAD is recorded as is.
- **Empty fires, fixture-broken, and the 14-day retry.** The routine's fire
  succeeds once the fire API accepts it, so a refused run looks like a
  successful fire that produced nothing. `scripts/plan_week.py` counts such
  empty fires per cell: successful non-bare eval fires that started after the
  cell's newest run on that model, are at least `FIRE_RESULT_WINDOW` old,
  started within `RETRY_AFTER` (14 days) and no earlier than
  `EMPTY_FIRES_SINCE` (fires under the new delivery only). At
  `BROKEN_AFTER_FIRES` (2) the cell becomes a `fixture-broken` work item and
  is not fired; once those fires are 14 days old they stop counting and the
  cell is tried again. A fire still waiting for its result holds the cell
  back from a second fire. A routine outage is not a broken fixture: each
  fire is classified once, as young, delivered (a run of the cell is stamped
  within `FIRE_RESULT_WINDOW` of its start, gates' output-only
  `run_stamps_on_model`) or empty. Each empty fire is then judged on its own
  window, `OUTAGE_GAP` (60 minutes) either side of its start (#583: centered
  on the fire, so its verdict depends only on fires near it and cannot move
  when a fire hours away ages out). One with no delivered or young fire in
  its window whose window's empty fires cover at least `OUTAGE_CELLS` (3)
  cells is an outage fire (2026-11-01: six fixtures fired, none produced
  anything); a delivered fire 45 minutes or more after the window's first
  empty fire may be the breaker's own probe and does not count, and an
  empty fire at most 60 minutes before an outage fire with no delivery
  between is one too, so a slow onset's first fire is excused: each cell's earliest, at most `OUTAGE_EXCUSES` (1) within
  `RETRY_AFTER`, is excused, and any later one counts, so fixtures broken
  together still go fixture-broken, one fire later. One with a young fire in
  its window waits. Each recent chain of outage fires is a `routine-outage`
  work item. The routine is down from the start of an outage fire until a
  paired eval fire on a known cell delivers (or, for the breaker only,
  once fires 45 minutes old with nothing landed cover three cells in one
  window with no delivery in or after it, so a burst trips it within the
  hour). While down the planner holds improve and bare fires and sends one
  probe at a time, a paired eval fire on any schedulable cell (settled and
  fixture-broken ones included), fewest empty fires first, then the oldest
  last fire, and none while a probe under 45 minutes old has landed
  nothing; every plan lists a `routine-down` work item. Probes never count:
  an empty fire sent while the routine was down is a down fire, unless it
  is an outage fire in the outage's first 45 minutes, which keeps the
  outage rule (the backstop). Without that, a lone empty probe, a window of
  one cell, counted, and back-to-back outages benched the same healthy
  head-of-band cells (2026-10-31 and 2026-11-01). The ambiguity left: a
  window of fewer than three cells while the routine is up cannot be told
  from broken fixtures, so it counts.
- **The first regression rows after the switch compare copies, not an
  edit.** The previous window of with runs tested the deployed copy, the
  next one main's, so a first regression row on a fixture whose context
  deployed an older copy compares the deployed copy with main's, not a skill
  edit.
- **A description that grows can exceed a thin budget.** Main's copy is
  sized into the with arm, so a skill-description growth can push a thin
  catalog budget over: the cms-platform fixtures have 156 bytes of catalog
  headroom. The run then refuses `budget_exceeded` (naming main's copy and
  its commit), and the cell becomes a fixture-broken item after two fires.
  Raising a budget is a reviewed PR.

## Addendum: fleet hooks are part of the deployed context (Adam, 2026-11-02)

**Addendum — fleet hooks are part of the deployed context (Adam, 2026-11-02).** An arm that stands for the real setup (in-place `with`/`without`; guidance `full`/`full-minus-section`, plus `section`/`none` when the fixture opts in) runs the fleet hook runner the context deployed. The runner is frozen from the context repository at `context.revision` (for a guidance fixture, from _agent-guidance at the guidance revision the run loads) and must equal what that revision shipped, or the run refuses with `fleet_hooks_unproven`. The hooks are installed the way ADR 0020's installer does it (config-based `hook.*` through a remote-scoped `includeIf`, never `core.hooksPath`), only inside the arm sandbox, which is proven by a harness-controlled marker, and on Git 2.54 or later. A fixture opts in with a key that is part of its fixture digest. The digest of the runner and hook set an arm received is recorded in its `context`, validated at ingest, and joins `pair_key` and `arm_context_digest`, so hooked and unhooked runs never pool, even for a context pinned after 2026-10-21 whose `fixture_digest` would otherwise not change. Isolation, bare and section-alone arms never run hooks unless the fixture opts its alone pair in. The harness's own git commands never run hooks.

Adam approved this text, revised to add the pooling key from the round-8
review, on 2026-11-02 in the project thread.

### Build

The design and the review findings behind it are
[skills-evals#535](https://github.com/Adam-S-Daniel/skills-evals/issues/535).
The build lands in stages, one pull request each, and no fixture opts in
until the last:

1. This addendum, Git 2.54 or later where arms run, `harness.git_version`
   in every summary, and the opt-in key `fleet_hooks: true` (a literal
   boolean in `fixture.yaml`, so part of `fixture_digest`), which the
   planner holds and the harness refuses (`git_too_old_for_fleet_hooks`)
   on an older Git. CI's runner already ships a newer Git, so `ci.yml`
   only checks it (`scripts/dev_setup.sh --check-git`). The routine
   container ships Ubuntu's Git 2.43 (adam-agentskills ADR 0020), and its
   setup script is not in this repository: it needs the zlib, OpenSSL and
   libcurl headers and then `bash scripts/dev_setup.sh --build-git
   /usr/local`, which builds the pinned Git 2.56.0 (the release ADR 0020's
   installer snippet builds) from kernel.org's tarball
   after checking its sha256.
2. The frozen hook set and its proof (`fleet_hooks_unproven`).
3. Injection inside the arm sandbox.
4. The pooling key.
5. The seed audit and the first fixture opt-ins.

Stages 2 to 4 are `harness/fleet_hooks.py`, wired into the in-place pair
(`run_eval._in_place_plan` and `_prepare_in_place`), and
`test/issues/test_issue_535_fleet_hooks.py`:

- **Frozen set and proof.** For a skill fixture the set is what the
  context repository shipped at `context.revision`, read from its Git
  objects where the sync delivers it: `.githooks/agent-checks`,
  `.githooks/dated-phrasing.js`, `.githooks/dated-phrasing-allowlist.txt`,
  `.githooks/dated-phrasing/package.json` and `package-lock.json`, and
  `.claude/hooks/agent-checks-guard.sh` (the layout of cms-platform and
  repo-settings on main). A guidance fixture takes the same files from
  _agent-guidance's `templates/agent-checks/` at the guidance revision the
  run loads. The context repository must belong to a fleet owner, or no
  fleet hook would fire in its clone. A missing file refuses the plan with
  `fleet_hooks_unproven`, before any paid call. markdown-it is installed
  once per plan with `npm ci --ignore-scripts` from the frozen lockfile,
  outside the sandbox (`fleet_hooks_install_failed` when it fails), and
  that directory is then read-only and write-denied to the arm. Each arm
  gets a read-only copy in its scratch at `fleet-hooks/`, beside `ws/` and
  `tmp/`, with the set under `.githooks/` as the runner expects it. A
  hooked fixture's `env:` may not name `GIT_CONFIG*`
  (`fleet_hooks_git_config_env`). Both in-place pairs are hooked: the skill
  pair and the guidance pair (`full`/`full-minus-section`).
- **Injection.** The agent's environment alone gets nine
  `includeIf.hasconfig:remote.*.url:<prefix><owner>/**.path` keys (the
  installer's three URL prefixes for `Adam-S-Daniel`, `adam-s-daniel` and
  `jodidaniel`) through `GIT_CONFIG_COUNT`/`KEY_n`/`VALUE_n`, pointing at a
  frozen include of `hook.agent-checks-<event>.event`/`.command` keys for
  `pre-commit` and `pre-push`, plus `AGENT_CHECKS_LOG=off` and
  `AGENT_CHECKS_DATED_PHRASING_MODULES`. The workspace gets the context
  repository's GitHub URL as `origin`; a seed that already has an `origin`
  is refused (`fleet_hooks_origin_exists`). The hook command reads the
  harness's own network namespace id (`/proc/self/ns/net`) from
  `fleet-hooks/harness-netns` and runs the frozen runner only when its
  own differs, that is inside the sandbox, and looks nothing up on `PATH`
  before that check (`read`, `/usr/bin/readlink`, `/usr/bin/bash`), since
  outside the sandbox `PATH` is the agent's; anything else exits 0, so a
  Claude Code hook's commit runs no `.agent-checks/local.sh`. The command
  runs the frozen runner even when the seed carries no `.githooks/`,
  since the context repository's clone would. The directory is
  write-denied (`Edit` deny rules and `sandbox.filesystem.denyWrite`), its
  tree digest (the root's mode, and every entry's path and mode with a
  file's bytes or a link's target, directories included) is read before the first turn and
  after each, and any change is `agent_wrote_agent_config`. The frozen
  `agent-checks-guard.sh` is the arm's one PreToolUse hook, through
  `--settings`, with the sync's matcher and timeout. A Claude Code hook
  runs outside the sandbox with the CLI's environment and the workspace as
  its cwd, so the command `cd`s into the frozen directory and runs
  `/usr/bin/bash` under `/usr/bin/env -i` with a fixed `PATH`, `HOME` set
  to that directory, `PYTHONSAFEPATH=1` and `PYTHONNOUSERSITE=1`: a module,
  interpreter or `.pth` the agent plants is never loaded. Harness Git runs no
  hook: workspace, harness-repository and context Git strip `GIT_*` and
  read no global or system config.
- **Pooling key.** `context.fleet_hooks_digest` (sha256 over each frozen
  file's path, mode and bytes and the injected include, environment and
  guard registration, with the arm's directory as a placeholder) is in a
  hooked arm's summary and absent otherwise; ingest checks it when
  present. compute_gates appends it to `pair_key` and
  `arm_context_digest` only when the key is present (an explicit null is
  malformed, as at ingest), so an unhooked run's keys are byte-for-byte
  what they were. For skill rows this is what separates hooked runs. For
  guidance rows it is defensive: in-place guidance runs are not pooled by
  the gates today (they record no `guidance_digests`, a gap that predates
  this addendum), and the isolation runs that are pooled are never hooked.
- **Not built here: the guidance alone pair.** The addendum's "plus
  `section`/`none` when the fixture opts in" has no opt-in yet; the alone
  pair never runs the hooks. Follow-up: [skills-evals#605](https://github.com/Adam-S-Daniel/skills-evals/issues/605). Until then a hooked section
  whose in-situ verdict is `retire` while it helps alone reads, as
  before, "the rest of the guidance covers it", though the fleet hooks
  may be what covers it; no hooked in-place guidance run reaches the
  gates yet.
- **Known, for the stage 5 audit.** `fleet_hooks_origin_exists` refuses
  at arm time, not at plan time, because it depends on the seed's setup, so
  the first arm of a pair can be paid for before its sibling refuses. Since
  [#605](https://github.com/Adam-S-Daniel/skills-evals/issues/605), the plan
  itself refuses a host without a namespace id (`fleet_hooks_no_receipt`),
  without `python3` where the guard looks (`fleet_hooks_no_python`), or whose
  managed settings set `disableAllHooks` or `allowManagedHooksOnly`
  (`fleet_hooks_managed_hooks_off`). `run_priors` and the regression window
  group by `fixture_digest` and the hook digest together. The receipt rests on the sandbox's `--unshare-net`, which the tests stand
  in for with `bwrap --unshare-net`, and on the live probes below. The CLI was seen to
  rewrite `GIT_CONFIG_*` for the Git it runs itself (dropping the include
  pairs and setting `hook.<event>.enabled=false`). One live call on WSL
  (Claude Code 2.1.316, Git 2.54.0, sandbox on; 2026-11-02, recorded on
  [#605](https://github.com/Adam-S-Daniel/skills-evals/issues/605#issuecomment-6590008657))
  showed it does not do so for sandboxed Bash tool commands: it appends
  two `safe.directory` pairs and keeps the include at index 0, an
  included pre-commit hook fired, and it fired in a network namespace
  other than the launching process's. The cloud container probe (2026-11-03)
  matched it, and no Actions runner hosts a hooked arm; both are recorded in
  [ADR 0016](0016-the-arm-sandboxs-network-namespace-marks-where-fleet-hooks-run.md). And the agent can
  still switch its own hooks off, by `git remote set-url origin` to a
  non-fleet URL or `env -u GIT_CONFIG_COUNT`: the guard stops habit, not
  intent, and CI's required `agent-checks` is the enforcement. In a
  no-network arm, `git push` to the injected `origin` fails at connect
  (exit 128) before `pre-push` runs, so the runner's pre-push refusals
  fire only for pushes to local-path remotes; a later fix could add a
  `url.<local bare repository>.insteadOf=https://github.com/<repo>.git`
  rewrite, so the configured URL still matches the include while the push
  lands locally (follow-up).

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
