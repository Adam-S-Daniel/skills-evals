# ADR 0014: A skill removal pull request merges automatically, with no human review

- **Status:** accepted (2026-10-26) as the decision; the auto mode it allows
  is built but not switched on. `evals/gate-policy.yml` keeps
  `retirement_mode: proposal`, and the scheduled workflow has no write
  credential for adam-agentskills yet.
- **Issue:** [#70](https://github.com/Adam-S-Daniel/skills-evals/issues/70)
  (part 2; part 1, the verdict, is
  [#411](https://github.com/Adam-S-Daniel/skills-evals/pull/411)).
- **Deciders:** Adam, directly: "Build it" for automatic removal of
  nonperforming skills (2026-10-25), and, at 23:14 UTC the same day, that
  removal pull requests auto-merge with no human review despite the fleet
  rule, with exception ADRs. On 2026-10-26 he decided results are not
  signed: the gate guards against honest mistakes only.

## Context

The fleet guidance says "PR + auto-merge is not a sanctioned bot-write
path", with named exceptions (skills-evals' roster PR, repo-settings
ADR 0003, recorded here as [ADR 0003](0003-roster-merges-automatically.md)).
adam-agentskills adds its own one-way doors: a skill basename, once shipped,
keys every consumer's `skills.lock` and `setup.sh` links, and a change to one
gets an adversarial round before merge (its `AGENTS.md`, "One-way doors get
an adversarial round").

The eval-loop thresholds design of 2026-10-25 (version 2, kept outside this
repository; its "Decisions for Adam" list) defaulted to "Adam merges; asked on a card". Adam chose the
opposite: a removal the verdict supports should land without waiting on him.
The verdict is built to make a wrong removal unlikely, not impossible: the
run is the unit, cells pool only runs of the content on main, a cell is
`no-benefit` only at two fixed looks (at least ten counted runs per arm),
every fixture on main crossed with every current roster model must be
`no-benefit`, any agent-errored trial blocks it, any benefit keeps, and
compute_gates lets one skill retire per evaluation (harness/gates.py).

## Decision

1. In `retirement_mode: auto`, `scripts/retire_skill.py` opens a removal
   pull request in adam-agentskills and enables auto-merge (merge commit).
   No human reviews it; adam-agentskills' required checks still gate it.
2. It acts only from the scheduled workflow (`GITHUB_EVENT_NAME` is
   `schedule`), never from a dispatch, a pull request or a terminal.
3. At most one removal pull request (head `retire-skill/<skill>`) is open
   at a time; an open one holds the slot whatever the newest verdict says.
4. It refuses a skill whose basename is not found exactly once across the
   registry checkouts it is given, or whose copy is not a real
   `plugins/<plugin>/skills/<skill>/` directory of adam-agentskills.
5. The pull request carries the whole removal: the skill directory, the
   plugin's patch version in both manifests (adam-agentskills ADR 0009), and
   a `docs/skill-impact.md` `remove` entry.
6. In `retirement_mode: proposal` (the committed value), a `retire` verdict
   files or updates one skills-evals issue instead, and a human removes.
   Switching to `auto` is Adam's call, made in `evals/gate-policy.yml`.

## Consequences

- **This ADR is one of three.** The exception must also be recorded in
  repo-settings (a bot write path that merges into a protected default
  branch, and whatever credential or ruleset change it needs) and in
  adam-agentskills (a removal of a shipped skill without the adversarial
  round its `AGENTS.md` requires of one-way doors). Neither is written
  here; auto mode stays off until both exist.
- **Auto mode needs a credential that does not exist.** The scheduled job's
  own token can write skills-evals issues only. Auto mode needs a GitHub App
  with contents and pull-requests write on adam-agentskills alone, minted
  immediately before use; until it exists the workflow allows only
  `proposal` and exits 2 on `auto`, rather than skipping quietly.
- **A removal is a one-way door in its consumers.** Every `skills.lock`
  that pins the plugin's bundle digest goes stale when the removal merges,
  and must be re-pinned. adam-agentskills' required checks are what stop a
  removal that breaks its own tree; a failed check leaves the pull request
  open, which holds the one slot until a human closes it.
- **Results are trusted as written.** Anyone who can write the results
  branch can make a skill retire; equally, anyone who can merge to
  adam-agentskills can remove one. The gate guards against honest mistakes
  (a changed fixture or skill, errored trials, a copy of a run ingested
  twice), not forgery (Adam, 2026-10-26).
