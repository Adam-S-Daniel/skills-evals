# ADR 0006: Run objective commands with isolated process state

- **Status:** accepted (2026-10-04); amended 2026-10-04 to reach the
  harness's `node` on hosts without one in `/usr/bin` or `/bin`
  ([#253](https://github.com/Adam-S-Daniel/skills-evals/pull/253)); amended
  2026-10-05 so a bare `node` argv uses that same `node`
  ([#260](https://github.com/Adam-S-Daniel/skills-evals/pull/260)).
- **Issue:** [#93](https://github.com/Adam-S-Daniel/skills-evals/issues/93).
- **Deciders:** Adam, who approved adding the check prerequisite on 2026-10-04.

## Context

Some fixtures need to prove that the final workspace's program actually
works. Matching printed `PASS` text cannot establish its process exit status.
The agent wrote this workspace and may have modified the program under test;
executing that code is the intended measurement and also the trust boundary.
Both the CI harness and the local harness publish check details, and the
local harness's guarded CLI launch must not become a command-check shortcut.

## Decision

Add the opt-in `command_succeeds` objective check. It takes a nonempty `argv`
list of strings and runs it directly, without a shell or interpolation, in
the arm's final workspace with closed stdin. Only exit zero passes. Invalid
arguments, spawn failure, nonzero exit, and timeout have separate named
results. `timeout_s` defaults to 30 seconds and must be finite, positive,
nonboolean, and at most 60 seconds.

Resolve bare `bash`, `sh`, `python3`, and `node` only at fixed `/usr/bin` or
`/bin` locations, never through a workspace name. The one exception is `node`
on a host with neither fixed location: it resolves to the harness's own `node`
described below, under the same refusals. Other
entrypoints must resolve inside the workspace; escaping symlinks fail.
Direct `claude` and `claude.exe` entrypoints fail. Build the child environment
from constants, with throwaway HOME, XDG/config/runtime/temp directories,
and a fixed PATH headed by a private `claude` refusal executable. No parent
variables, credentials, `CLAUDE_BIN`, or local launchers are inherited.
The PATH is the refusal directory, then `/usr/bin:/bin`. When neither fixed
location holds `node` (GitHub's runner image keeps it in `/usr/local/bin`,
`setup-node` in its tool cache), the harness's own `node`, resolved from the
harness's PATH and refused if it lies inside the workspace, is appended as a
throwaway directory holding only a `node` symlink. A verifier that runs `node`
through PATH, or names `node` as its argv entrypoint, then scores the same on
every host. Only `node` is added: no
current check needs another host tool, and appending a whole directory such
as `/usr/local/bin` would expose every tool installed there.
The existing agent and local allow-lists retain login state, so neither fits.

On Linux, probe a fixed `unshare --net` invocation with a bounded harmless
command. Use a network namespace when the platform permits it; otherwise
run with the same process-state isolation and report `network=unavailable`.
No heavy sandbox dependency is introduced. On POSIX timeout, terminate
the command's own process group and reap its direct child, never
unrelated processes. Cleanup also has a bounded wait.

Capture stdout/stderr in temporary files, avoiding unbounded memory reads.
Published diagnostics contain only named status, exit code, network status,
and capped output-byte metadata with a truncation marker. Free-form output
and exception text are suppressed: arbitrary program text can reveal host
paths, environment values, or sensitive workspace contents, and a regex
redaction cannot prove it safe.

## Consequences

Existing fixtures keep their scores: no fixture changes here, and this type
runs only when explicitly selected. The same registry route supports CI and
local objective scoring. Ordinary indirect `claude` lookup reaches the
private refusal stub instead of bypassing the local launch-time guard.

This is process-state hygiene with optional network isolation, not a full
filesystem or process sandbox. Code can read absolute host paths, invoke
absolute binaries, modify its environment, or deliberately evade PATH.
An interpreter can therefore intentionally invoke an absolute CLI path;
this check does not claim to prevent that. It also does not cap temporary
disk usage, CPU, descendant escape via a new session, or network access when
namespace creation is unavailable. Fixtures must not test hostile code that
needs those stronger boundaries. No real CLI or paid evaluation is used to
verify this change.

## Alternatives considered

- Printed success markers: rejected because they do not prove an exit status.
- The existing child environment helpers: rejected because they preserve
  authentication and user configuration required by agent calls.
- A mandatory container or filesystem sandbox: deferred because it adds
  dependencies and platform setup beyond this objective-check prerequisite.
- Publishing redacted program output: rejected because arbitrary output can
  encode sensitive values in forms no finite redaction list recognizes.

## References

- [Issue #93](https://github.com/Adam-S-Daniel/skills-evals/issues/93): fixture
  work that needs this prerequisite.
- [Command scorer](../../harness/scorers/commands.py): the execution boundary.
- [Design contract](../../DESIGN.md): fixture-facing check contract.


## Workspace Git addendum (2026-10-07)

[Issue #343](https://github.com/Adam-S-Daniel/skills-evals/issues/343) found
that post-arm staging, diff collection, and Git-state scorers executed Git
against agent-controlled metadata. Git configuration, hooks, filter/diff
attributes, includes, or repository redirects can therefore execute workspace
code in the harness process environment after the arm's sandbox has ended.
The objective-command boundary above does not govern these bookkeeping calls.

Route every bookkeeping Git call through [one helper](../../harness/workspace_git.py).
Use a fixed executable and constants-only environment, forbid transports,
disable executable configuration and external diff/textconv, and operate on
private metadata with generated configuration. Parse a regular private copy
of repository configuration with Git's parser and `--no-includes` solely to
validate it; never let a bookkeeping command load workspace configuration.
Record baseline `.git` identity plus framed configuration/`info/`/`hooks/` digests and
metadata bytes in harness memory. Remove all private metadata before the arm,
then restore it only during bounded post-arm calls; staged index updates stay
in memory between calls. A changed baseline, executable key or driver, symlink,
redirect, or alternate object store returns `workspace_git_tampered` and skips
scoring. Independently inspect standalone nested repos and bare ref sources;
linked worktrees get a structural report without a patch or followed redirect.
Staging copies working files privately and adds validated nested HEAD gitlinks,
so root `git add` cannot discover nested configuration indirectly.

The `-c` overrides (fsmonitor, hooks path, external diff, pager, editor,
SSH, credential, askpass, proxy) are a second layer: tests prove each wins
over repository-local config when Git reads that config directly.

Consequences: benign baseline config/`info/`/`hooks/` edits are also refused; linked
worktree patches are unavailable; metadata copies consume memory and disk I/O.
The arm has ended before ephemeral collection files exist. This addresses Git's
implicit execution surfaces, not arbitrary concurrent host processes or the
intentional execution of a fixture program by `command_succeeds`/`repo_tests`.

Alternatives: `-c` overrides alone cannot enumerate every include, driver, or
repository redirect and still let Git parse agent files. A persistent private
metadata directory is writable/discoverable during an arm and cannot establish
trust merely by its pathname. Refusing all nested repositories would discard
valid fixture evidence; read-only snapshots preserve it without following
linked layouts. [Real marker regressions](../../test/issues/test_issue_workspace_git.py)
prove seven original execution vectors and lock in the refusals and legitimate
ref/worktree behavior without network or live agent calls.
