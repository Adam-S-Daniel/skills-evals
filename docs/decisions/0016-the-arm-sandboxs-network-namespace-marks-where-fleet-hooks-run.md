# ADR 0016: The arm sandbox's own network namespace marks where the fleet hooks run

- **Status:** accepted (2026-11-03). Recorded before the first fixture opts
  into `fleet_hooks: true`, as [ADR 0012](0012-ab-runs-in-the-deployed-context-minus-the-subject.md)'s
  fleet hooks addendum and [#605](https://github.com/Adam-S-Daniel/skills-evals/issues/605)
  item 4 require.
- **Deciders:** Adam approved the fleet hooks addendum, including the
  harness-controlled sandbox marker, on 2026-11-02
  ([#535](https://github.com/Adam-S-Daniel/skills-evals/issues/535)). This
  record holds the measurements that marker rests on.

## Context

A hooked arm's include runs the frozen fleet runner only when the hook's
own network namespace (`/proc/self/ns/net`) differs from the one the
harness wrote to `fleet-hooks/harness-netns`
(`harness/fleet_hooks.py`, `include_text`). The marker separates a commit
made by the agent's Bash tool, which Claude Code's sandbox runs under
`bwrap --unshare-net`, from a commit made by a Claude Code hook, which runs
outside the sandbox with the CLI's environment and must not run the agent's
`.agent-checks/local.sh`. CI's tests stand in for the sandbox with
`bwrap --unshare-net`. So the marker is only as good as the claim that
the real CLI puts sandboxed Bash in a new network namespace, on every
host that runs a hooked arm, and leaves the injected `GIT_CONFIG_*` include
in place there. Environment variables could not serve as the marker,
because unsandboxed processes inherit them. Seccomp status could not either,
because it depends on the host ([ADR 0011](0011-sandbox-agent-arm-network.md)
measured it on WSL only).

## Decision

1. The network namespace receipt is the marker. Hooks fire for sandboxed
   Bash only, as built.
2. A hooked arm runs only where the claim has been probed live:
   - **The cloud routine container** (ADR 0010's in-place runner). Probed
     below.
   - **Adam's WSL machine.** Probed below.
3. **No GitHub Actions runner hosts a hooked arm.** `eval.yml` refuses every
   in-place fixture, in its plan job and again before its mint
   ([#587](https://github.com/Adam-S-Daniel/skills-evals/issues/587)). Only
   the in-place plan (`run_eval._in_place_plan`) delivers the hooks. So the
   CI runner needs no probe. CI's `test` job runs the
   hooks only under the `bwrap --unshare-net` stand-in. If `eval.yml` ever
   learns to host in-place pairs, it must repeat this probe on the runner
   before it runs a hooked fixture.
4. Re-probe when a CLI release changes the sandbox, or when a new host
   class starts running arms. Use the same command, and record the result
   here as a dated entry.

## Probes

**Method (both hosts).** Make a scratch repository whose `origin` is a fleet
URL. Export one include pair:
`GIT_CONFIG_COUNT=1`, `GIT_CONFIG_KEY_0=includeIf.hasconfig:remote.*.url:https://github.com/Adam-S-Daniel/**.path`.
The include holds a `hook.probe` pre-commit command that appends
`readlink /proc/self/ns/net` and `$GIT_CONFIG_COUNT` to a log. First, make
a control commit from the launching shell. Then make one headless call:

```
claude -p --model haiku \
  --settings '{"sandbox":{"enabled":true,"autoAllowBashIfSandboxed":true}}' \
  --allowedTools Bash "<run: readlink /proc/self/ns/net; env | grep ^GIT_CONFIG; git commit --allow-empty -m probe; cat hook.log>"
```

The call is one model request on plan allowance and produces no eval data.

- **2026-11-02, WSL on the durable workstation.** Claude Code 2.1.316, Git 2.54.0.
  - Sandboxed Bash saw `GIT_CONFIG_COUNT=3`. The harness's include was
    still at index 0, and the CLI had added two `safe.directory` pairs.
  - The included hook fired in `net:[4026532234]`. The launching process
    was in `net:[4026531833]`.
  - Recorded on [#605](https://github.com/Adam-S-Daniel/skills-evals/issues/605#issuecomment-6590008657).
- **2026-11-03, claude.ai cloud container.** This is the hosted container
  class the eval runner routine fires into. The probe ran in a project
  session's container, not inside a routine run. Ubuntu 24.04.5, Claude
  Code 2.1.317, Git 2.56.0.
  - The control commit's hook fired in `net:[4026531833]` with count 1.
  - Sandboxed Bash ran in `net:[4026532267]` and saw `GIT_CONFIG_COUNT=3`,
    with the include still at index 0 and two `safe.directory` pairs at
    indexes 1 and 2.
  - Its `git commit` fired the included pre-commit hook in
    `net:[4026532267]`, and the hook logged count 3.
  - The commit itself then failed in that container's own commit-signing
    step (`fatal: failed to write commit object`). That happens after
    pre-commit and does not touch the marker.

No link: these were local probes, and the scratch repositories were
deleted.

## Consequences

- The fleet hooks addendum's open measurement (#605 item 4) is closed for
  every host that runs a hooked arm today. Fixtures may opt in.
- The remaining gap is the one the addendum already names. A future CLI
  could run sandboxed Bash in the launching process's namespace. If it
  did, the hooks would silently never fire (the safe direction): runs
  would still pool under their hook digest and measure an unhooked arm.
  Decision 4's re-probe is the guard against that.
- A per-arm canary would catch that case without a re-probe. It is not
  built: an arm has no harness-run step inside the CLI's sandbox to host
  one.
