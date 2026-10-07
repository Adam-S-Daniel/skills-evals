# ADR 0011: Agent arms run behind Claude Code's network sandbox, delivered by `--settings`

- **Status:** accepted (2026-10-07)
- **Issue:** none; found while preparing the real-work fixtures
  (`evals/real-work/*`), whose seeds are public repositories' pre-fix trees.
- **Decider:** Adam, who chose the `--settings` delivery on 2026-10-07 over a
  workspace `.claude/settings.json` with a `seed_guard` exception.

## Context

A real-work arm starts from a public fleet repository's tree before a merged
fix. With GitHub reachable, the agent can `git clone`, `curl` or WebFetch the
repository and read the fix, which is the fixture's answer key. The fleet's
deployed sites serve the built fix as well
(`https://adamdaniel.ai/admin/live-url-derive.js` carries cms-platform#693's).
Arms already get an empty `GH_TOKEN`/`GITHUB_TOKEN`, but a public repository
needs no token, and nothing restricted the network: ADR 0006's
`unshare --net` covers objective-check commands only.

Claude Code's sandbox (https://code.claude.com/docs/en/sandboxing,
https://code.claude.com/docs/en/settings-reference) confines Bash, PowerShell
and Monitor commands and their children: on Linux a network namespace with no
route out except a proxy that checks each hostname. It does not cover the
built-in Read, Edit, WebFetch and WebSearch tools, hooks or MCP servers.
Subagents run in the same process and use the same sandbox. By default a
sandbox that cannot start (Linux needs `bubblewrap` and `socat`) is skipped
silently.

## Decision

Every agent arm, skill or guidance, on every turn including `--resume`
follow-ups, gets `run_eval.arm_isolation_flags()`:

- `--settings` with `run_eval.arm_sandbox_settings()`: `sandbox.enabled`,
  `failIfUnavailable: true`, `allowUnsandboxedCommands: false`,
  `network.strictAllowlist: true`, `network.allowedDomains: []`, and
  `network.deniedDomains` for GitHub (`github.com`, `*.github.com`,
  `codeload.github.com`, `githubusercontent.com`, `*.githubusercontent.com`),
  the deployed sites (`adamdaniel.ai`, `jodidaniel.com` and their subdomains)
  and `cdn.jsdelivr.net`;
- `--disallowedTools WebFetch,WebSearch`, because the sandbox does not reach
  those tools.

A CLI that refuses to start (stderr `sandbox required but unavailable`, exit
1) fails the arm with `sandbox_unavailable`. The judge, the guard and canary
probes, `deps:`/`setup:` and objective commands are not changed.

`--settings` rather than a workspace `.claude/settings.json`: command-line
settings outrank project settings, `allowUnsandboxedCommands: false` there
makes the sandbox admin-required so a repository's settings files can no
longer loosen it (`excludedCommands`, proxy ports and similar are ignored),
and `strictAllowlist` is not honored from project settings at all. The agent
can write its workspace's `.claude/`, so a file there would have needed a
tamper check; a flag needs none, and nothing lands in the workspace for
`seed_guard` or a scoring check to see.

## Consequences

- Measured on CLI 2.1.292 (2026-10-07), auto mode, with these flags: `curl`
  to `github.com` and `raw.githubusercontent.com` and `git ls-remote` against
  GitHub fail with `CONNECT tunnel failed, response 403` and the sandbox's
  `host is on the deny list`; `example.com` fails with `host is not on the
  allow list`; WebFetch is not available; the session itself (API traffic)
  completes. With `socat` missing the CLI exits 1 before any model call.
- Arms have no network from Bash at all. A fixture whose agent needs a
  package registry during the run must install it in `deps:` or `setup:`,
  which run outside the sandbox.
- A host on the CI runner or routine must have `bubblewrap` and `socat`, or
  every arm errors with `sandbox_unavailable`.
- Reads are not restricted. A sandboxed command and the Read tool can read
  anything the user can, including this checkout's
  `evals/real-work/*/checker/` and `solution.patch`. Closing that takes
  `sandbox.filesystem.denyRead` for the checkout (and sibling clones) plus
  `Read(//<path>/**)` deny rules for the Read tool, in the same `--settings`.
- With `strictAllowlist` every unnamed host is refused too, so the deny list
  is what still holds if a later change opens an allowlist: it is refused in
  every permission mode, even inside an allowed wildcard.
