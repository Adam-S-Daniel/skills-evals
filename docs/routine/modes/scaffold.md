SCAFFOLD MODE:
**Scaffold mode** (payload `"mode": "scaffold"` only). You turn ONE miner
candidate into ONE draft real-work fixture. You never open, edit or
comment on a pull request, never push any branch but
`claude/scaffold-<fixture id>`, and never push to `main` or
`persistent/*`.

1. Check out `Adam-S-Daniel/skills-evals` at `origin/main`. Install the
   pins: `python3 -m pip install --user pyyaml==6.0.3`.
2. Mine, from checkouts of `_agent-guidance` (its `repos.yml` and
   `.github/workflows/sync.yml`):
   `python3 scripts/mine_real_work.py mine --registry <ag>/repos.yml --candidate <the payload's candidate key> --out /tmp/rw/candidates.json`.
   Find the payload's `candidate` key in it; if it is absent, stop.
3. Clone the candidate's public repository to `/tmp/rw/clone` (read only;
   never push from it). Run
   `python3 scripts/mine_real_work.py prepare --clone /tmp/rw/clone --base <base_sha> --merge <merge_sha> --test-file <each test file> --out /tmp/rw/rg/<key>`,
   run the tests in `red` and `green` with no network
   (`unshare --user --map-current-user --net --pid --fork --mount-proc -- ...`),
   write JUnit XML and `run.json`, and run `mine_real_work.py admit`.
   If the candidate is not admitted, stop.
4. Write `/tmp/rw/spec.json` (this is the only part you author):
   - `task_text`: the closing issue's title and body, verbatim, minus any
     section that describes the solution (a "Fix", "Proposed fix" or
     "Needs verification" section, a code sketch of the change) and minus
     its dates and version numbers ("found on 2026-10-06", "at v0.1.148"),
     keeping one only where dropping it would very significantly
     disadvantage the agent relative to the one that did the original
     work; then one line stating the task,
     then a short "Interface the reviewer's tests
     use" paragraph naming only what the hidden tests check verbatim.
     Never paste a line from the pull request's diff.
   - `interface_strings`: 1 to 32 strings the hidden tests check verbatim.
   - `checker`: `files` (the admitted test files), `argv`, `fail_to_pass`
     and `pass_to_pass` (per-test selections, each run under 60 s).
   - `deps` (only if the tests need an npm lockfile install) and `trim`
     (only paths over the caps the defaults do not already trim).
   - `issue`: omit it to use the single closing issue.
   - The closing issue's text is the payload's `issue_snapshot` (`title`,
     then `body`); write `task_text` from it, never from the issue as it
     reads today. When `issue_snapshot` is null, omit `issue` only if the
     candidate's `closing_issues` is empty; otherwise stop: the fire
     workflow and the miner disagree, and a person must look.
5. Write the payload's `issue_snapshot` value, exactly as received (the
   JSON object, or `null`), to `/tmp/rw/issue-snapshot.json`; never edit
   it. Build and check:
   `python3 scripts/scaffold_real_work.py build --candidates /tmp/rw/candidates.json --key <key> --clone /tmp/rw/clone --spec /tmp/rw/spec.json --issue-snapshot /tmp/rw/issue-snapshot.json --context-repo Adam-S-Daniel/_agent-guidance=<ag> --context-repo <each registry in the candidate's skills.lock at base_sha>=<its checkout> --dest evals/real-work`.
   First make each of those checkouts full history with a current
   `refs/remotes/origin/main` (`git fetch --unshallow origin` if
   `git rev-parse --is-shallow-repository` prints true, then
   `git fetch origin main`). If fixture.yaml still has
   `guidance_revision: null`, push nothing and report it.
6. Commit ONLY `evals/real-work/<fixture id>/` on a new branch
   `claude/scaffold-<fixture id>` from `origin/main`, with the message
   `Scaffold real-work fixture <fixture id> (run <run id>)`, and push it.
   Verify with `git merge-base --is-ancestor <sha> origin/claude/scaffold-<fixture id>`.
   Do not open a pull request: `routine-scaffold-gate.yml` validates the
   branch and opens the draft PR.
7. Report: the branch, the commit sha, the `check --run` summary line,
   the spec's `task_text` sections you dropped and why, any date or version number you kept and why, and whether
   `issue_snapshot` was null or which issue number it named.
End the scaffold-mode final message with RESULT: ok|error|refused.
