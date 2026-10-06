## Repo-specific additions

**`AGENTS.md` in this repo is a generated artifact.** Everything above the marker
is `scripts/build-agents-md.sh` output — edit `agents-md/base.md` (or a file under
`agents-md/sections/`), never this file's managed half. CI regenerates and diffs
it, so a base.md edit without a regenerated `AGENTS.md` fails the build.

Why it is committed here at all, when `sync.sh` writes it everywhere else: the
sync excludes its own repo (`SYNC_SELF_REPO`), so for as long as this repo has
existed it was the one repo in the fleet whose agents never read the fleet's
guidance. Committing the rendered output fixes that and buys a second thing —
a PR that changes `base.md` shows the exact text ~20 repos are about to receive,
in the same diff, instead of deferring it to an async run after merge.

Regenerate with:

```bash
printf '%s\n%s\n' "$(./scripts/build-agents-md.sh)" \
  "$(sed -n '/^## Repo-specific additions/,$p' AGENTS.md)" > AGENTS.md.new \
  && mv AGENTS.md.new AGENTS.md
```

The recipe above is line-anchored, but between commit `c86465f` and this fix
some tooling split the file on the first OCCURRENCE of the marker substring
instead — and the managed block's own BEGIN header quotes the marker verbatim
(`DO NOT EDIT ABOVE "## Repo-specific additions"`), so that split anchored on
the header line rather than the real heading and treated the entire prior
managed block as repo-specific content to preserve. Every regen after that
prepended a fresh managed block on top of the old one, so the file carried two
managed blocks — including two contradictory copies of the skills-ecosystem
rule — for four commits (through `7b87581`). Because the recipe's own anchor
kept matching the same corrupted line, the doubled file was a fixed point of
regeneration, so the staleness check above stayed green throughout; only a
check that counts markers and asserts their order can tell a doubled file from
a well-formed one, which is what `scripts/check-agents-md.sh` does, and CI now
runs it ahead of the staleness check for exactly this reason.

**A new `##` heading in `agents-md/base.md` (or a new file under
`agents-md/sections/`) needs a row in `agents-md/eval-coverage.yml` in the
same PR.** Add it before the section lands, not after — CI's "Section manifest
covers every guidance heading" step (`scripts/check-guidance-coverage.js`)
fails otherwise, naming the heading and the two ways to close it: a `covered`
row pointing at a skills-evals fixture, or a `skipped` row giving a `reason`
and a `since` date. The same step also fails if a heading gets reworded
without updating the matching row's `heading` text (reported as a stale row,
with the nearest current heading offered as the likely rename target) or if a
row's `bytes` has drifted from the section's real size (fix with
`node scripts/check-guidance-coverage.js --write-bytes`).

**A PR that changes a `##` section's own extent — its body text, not just a
rename — needs an entry in [`docs/guidance-impact.md`](docs/guidance-impact.md)
in the same PR.** CI's "Guidance touch gate" step (`scripts/check-guidance-touch.js`)
fails otherwise, naming the section's `id` and the entry format. A pure
rename (the heading text changes, updated in `agents-md/eval-coverage.yml`,
body untouched) needs no entry; a body edit does, and a removed section
needs one typed `remove`. See that file's own header for the entry format
and what counts as a sufficient `Eval:` line.
