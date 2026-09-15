
## Gates

| Gate | How I ran it | Result |
|---|---|---|
| `check-guidance-coverage.js --check-bytes` (#119) | in the head tree | `28 gap · 1 skipped · 0 covered`, **exit 0** |
| … negative control | same, with the new manifest row deleted | **exit 1**: `heading ""fleet-guidance: current" is not "the guidance is in context"" … has no row` — the gate is real, and the row's `bytes: 1053` is what `--check-bytes` accepts |
| `check-guidance-touch.js` (#120) | a throwaway two-commit git repo built **under `$SP/r1w124/`** (ref tree = base commit, head tree = head commit) with a synthetic `$GITHUB_EVENT_PATH` | `1 section(s) touched, all have a sufficient docs/guidance-impact.md entry`, **exit 0** — verbatim the PR body's claim |
| `check-agents-md.sh` | head tree | exit 0 |
| "Self-guidance is current" | `printf '%s\n%s\n' "$(./scripts/build-agents-md.sh)" "$(sed -n '/^## Repo-specific additions/,$p' AGENTS.md)"` then `diff` | **clean** |
| `bridge-status.sh CLAUDE.md` | head tree | `bridge-ok` |
| `check-registry.js` | head tree | exit 0 |
| `check-cron-coverage.js` | head tree (a `git archive`, not a repo) → exit 1 `not a repository`; **re-run inside a real git repo built from the same tree** | **exit 0**, `All audited repos covered`. Identical on ref, so the exit-1 is an artefact of the archive, not the branch. |
| `.claude/settings.json` | `json.load` | valid |
| `bash -n` | all six touched shell files | clean |
| embedded python | `compile()` on both heredocs | clean; the hook's program is **pure ASCII** as its comment claims |

Docs: `agents-md/base.md` gains exactly one `##` section (21 → 22) with the eval-coverage row
(`status: gap`) and the `guidance-impact.md` entry (`- Eval: none — no fixture yet`) — the
combination the issue explicitly permits. `.claude/hooks/fleet-guidance.md` is byte-identical to
`agents-md/base.md` (and ends in a newline, which is what makes the hook's byte arithmetic exact).
`stub.md` and the regenerated `AGENTS.md` carry the same three new verdict bullets. The README
gains `## The load-time receipt` plus a pointer bullet, and its layout listing is updated.

**The two wording departures.** Both are justified and both are tested:

1. *"the paragraph in `base.md`'s 'Fleet guidance is delivered once per session' section"* — that
   heading exists only in `agents-md/stub.md`; `grep '^##' agents-md/base.md` has no match for it
   (verified on the ref tree, so this is not something the branch created). Splitting it — verdict
   lines to the stub, a new `##` section to `base.md` — is what makes #119's row and #120's entry
   applicable at all. Both gates pass.
2. *`agents-md: BEHIND (v<x> < v<y>)`* — two truncated sha256 digests have no ordering, so the
   literal form would assert something false. The replacement names which is which, and
   `assert_not_contains "$d/out_agents_behind" " < v"` forbids the original form specifically. Red
   at head under mutation `W5`.

## The workflow line, line by line

`git diff` of `.github/workflows/sync.yml`: **4 lines added, 0 removed, 0 modified.**

| Check | Result |
|---|---|
| exactly one `paths:` entry plus its comment | yes — 3 comment lines + `      - ".claude/hooks/instructions-loaded.sh"`, inserted after the `fleet-memory.sh` entry |
| any `uses:` changed | no — all four `uses:` lines (`actions/checkout@34e114876b0b11c390a56381ad16ebd13914f8d5`, two × `actions/create-github-app-token@bcd2ba49218906704ab6c1aa796996da409d3eb1`) are byte-identical to ref; every one is a bare 40-hex SHA with no trailing version comment |
| any `${{ }}` inside a `run:` | none added. The one that exists — `if [[ "${{ inputs.dry_run }}" == "true" ]]` — is at ref line 146 and head line 150, i.e. pre-existing and untouched, and it interpolates a `workflow_dispatch` boolean, not a PR-controlled field |
| `pull_request` trigger added | no — triggers are `push` + `workflow_dispatch` on **both** trees; the only occurrence of the string `pull_request` in the file is inside a comment about token scopes |
| permissions | `permissions: contents: read` — identical on both trees |
| file still parses | `yq -e '.'` OK |
| the entry is *demanded*, not decorative | `test_sync_workflow_trigger` derives the watched set from `sync.sh`'s `$REPO_ROOT/…` references; the new `INSTR_HOOK_SOURCE="$REPO_ROOT/.claude/hooks/instructions-loaded.sh"` puts the path in the derived set, and the new assertion `sync trigger: on.push.paths covers .claude/hooks/instructions-loaded.sh` is one of the 103 |
