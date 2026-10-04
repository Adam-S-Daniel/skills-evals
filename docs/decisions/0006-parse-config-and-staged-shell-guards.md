# ADR 0006: Parse configuration values and staged shell guards before scoring

- **Status:** accepted (2026-10-04)
- **Issue:** Part of [the code-quality eval, #88](https://github.com/Adam-S-Daniel/skills-evals/issues/88).
- **Decider:** Adam approved both check types and a Bash parser dependency
  on 2026-10-04; the C58 worker package records that approval.

## Context

The code-quality eval needs evidence that a configuration contains an integer
width of 100 and that local hooks pass staged Go files to available tools.
Text matching credits comments, unrelated nested keys, string-valued numbers,
and disconnected shell guards. YAML's acceptance of JSON-looking text is not
evidence that a JSON manifest parses. Existing fixtures must keep their scores.

## Decision

Add two opt-in objective types, without changing existing checks:

- `parsed_config_values`: exact workspace-relative `paths`, explicit `format`
  (`yaml` or `json`), and optional `expected` entries shaped as
  `{path: [mapping, keys], equals: <typed value>}` or
  `{path: [mapping, keys], contains: <typed list member>}`. An omitted or empty
  `expected` list checks parsing only. Roots must be mappings; keys must be
  strings and values must be finite JSON-shaped scalars, lists, or mappings.
  PyYAML's composed tree rejects duplicate keys at every depth before
  construction; JSON uses `json.loads` with duplicate-key and nonfinite-number
  rejection. Recursive aliases, merge keys, custom tags, excessive depth or
  size, and nonmapping roots fail. Type and value must match recursively:
  booleans, integers, floats, and strings remain distinct.
- `shell_staged_tool_guard`: exact workspace-relative `paths` and a nonempty
  list of literal `tools`. Parse Bash with Tree-sitter and analyze paths through
  the AST; never execute the script. Each tool must have a reachable direct
  invocation, and every reachable invocation must receive a proven staged Go
  variable and be dominated by availability and nonempty-file facts. A branch
  where a tool is missing may skip with `exit 0`, but cannot exit nonzero.

Recognized shell sources are scalar `files=$(git diff --cached --name-only
-- '*.go')` (also `--staged`), or that diff piped to `grep '\.go$'` / `grep -E
'\.go$'`. Optional `--diff-filter=ACM` is accepted. The same substitution
inside `files=($(...))` produces an array. Scalar `$files` / `${files}` and
array `"${files[@]}"` arguments bind calls to the source. Arrays require a
`${#files[@]} -gt 0` nonempty test; scalars require `-n "$files"` (or the
negation of `-z`). These source shapes do not claim NUL-safe filename handling;
the check establishes staged provenance, not hook correctness for every name.

Availability is `command -v TOOL`, `type TOOL` / `type -P TOOL`, or `hash TOOL`.
A helper such as `have() { command -v "$1" >/dev/null 2>&1; }` is recognized
only when its entire body is that check, optionally redirected. `if`/`else`,
negation, `&&`, nested guards, and successful early exits propagate facts.
Reassignment invalidates provenance; branch joins keep only facts common to
all continuing paths. Constant false paths cannot supply an invocation.

Fail closed on `eval`, source/`.` commands, aliases, indirect expansions,
dynamic command names, arbitrary command substitutions, unsupported redirects,
loops, case statements, subshells, background execution, wrappers, and helper
bodies other than the availability check. Comments, literal strings, and
literal heredoc bodies never supply calls or guards. The implementation is a
bounded recognizer, not a general Bash interpreter; unsupported forms receive
named failure reasons.

Use exact pins `tree-sitter==0.26.0` and `tree-sitter-bash==0.25.1`. PyPI JSON
was checked on 2026-10-04: the latest non-prerelease releases were published
2026-06-30 and 2025-12-02, respectively, both older than seven days.
Install both in every workflow that installs the objective harness; there is
no requirements file or Python package manifest in this repository.

## Consequences

The new types reject deceptive evidence without altering old fixtures. Paths
must resolve to present regular files inside the workspace; symlinks escaping
it fail. Input is capped at 64 KiB, with bounded tree depth and node counts.
Failure details use fixed reasons and never echo file contents or parser errors.

The parser adds two small binary-wheel downloads to Linux CI (approximately
668 KiB runtime and 232 KiB grammar), and compiled extensions instead of a
pure-Python dependency. Supported wheels avoid compiler setup on ordinary
CPython runners; platforms without wheels require a build toolchain. Syntax
recovery nodes fail rather than being credited as valid code.

## Alternatives considered

**bashlex 0.18:** pure Python and cheap to install, but its latest PyPI release
is from 2023 and its documented parser omissions include Bash array syntax.
Array path passing and heredoc distinctions are required here. Tree-sitter's
maintained Bash grammar represents those constructs directly.

**Regular expressions or token matching:** cannot establish typed mapping
paths, control-flow dominance, or distinguish executable calls from strings.

**Executing hook scripts:** would cross a trust boundary, depend on installed
tools and Git state, and could run agent-authored commands. Parsing is hermetic.

## References

- [Tree-sitter Python runtime release](https://pypi.org/project/tree-sitter/0.26.0/)
- [Bash grammar release and wheel inventory](https://pypi.org/project/tree-sitter-bash/0.25.1/)
- [Bash grammar source](https://github.com/tree-sitter/tree-sitter-bash)
- [bashlex limitations](https://github.com/idank/bashlex#limitations)
