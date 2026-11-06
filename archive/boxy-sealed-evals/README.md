# Sealed eval lane on BOXY: archive (parked 2026-11-06)

**Status: parked, not merged, not in use.** On 2026-11-06 Adam chose to keep
evals in the cloud routines (a slimmer routine, both models per fire) and to
park the move to BOXY. Everything that work produced is kept here so it can be
picked up again; nothing here runs, and nothing on `main` depends on it. Do not
build on this branch without reading "Open questions" first: the code is from
2026-11-04 and `main` has moved since.

- This branch: `persistent/boxy-sealed-evals` (deletion-protected by the
  repository's `persistent/**` ruleset).
- The pull request it grew from, closed unmerged:
  https://github.com/Adam-S-Daniel/skills-evals/pull/780
- The tracking issue (labeled `on-hold`) is linked from the pull request.

## TLDR

A sealed Docker lane on BOXY (Docker Desktop 4.92, engine 29.8.0, WSL2) was
built and proven end to end with a real `claude setup-token`: the arm container
sits on an internal network with no route out, and its only path to the model
is a credential-proxy sidecar that holds the real token, so the arms (and any
hook) only ever see `dummy-not-a-token`. One real run (writing-adrs/bootstrap)
scored like the cloud runs, recorded meter snapshots, and cost $0.21. The work
stopped before the harness changes that would let the lane run in-place and
guidance fixtures (T8) and before the comparison runs (T9).

## What is on this branch

Reviewed and tested (the session that ran the BOXY work reviewed each diff):

| Commit | What |
| --- | --- |
| `6f1fa8fd` | Container mode for `scripts/local_eval.py` (`--container-token`), `scripts/container_eval.sh`, `docker/eval-runner/Dockerfile` (the starting point, from the cloud side). |
| `7e5e19ca` | `docker/eval-runner/seccomp-bwrap.json`; image rebuilt: Git 2.56 built from source and linked at `/usr/bin/git`, only the linux-x64 CLI binary (sha512-checked against the npm registry), Node 22, socat. |
| `8d9f3419` | Sidecars: `docker/eval-egress` (squid, CONNECT-only allowlist) and `docker/eval-credproxy` (nginx, replaces Authorization with the token from a file mounted into it alone; forwards only POST `/v1/messages` and `/v1/messages/count_tokens`). |
| `927eef94` | `/usr/bin/python3` link: the scorer sandbox and the fleet-hook guard only look in `/usr/bin` and `/bin`. |
| `5bdddc84` | Judge hardening from the cloud side (no tools, no GitHub or cloud credentials). **Not BOXY-specific: if it is still wanted, land it on `main` separately.** |
| `7ff39eba`, `82cd73fa`, `d3e22b21`, merged in `157044f0` | `local_eval`: `CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC` on the child allow-list; `ANTHROPIC_BASE_URL` allowed under `--container-token` only as `http://<one-label name>:<port>`. `container_eval.sh`: one internal network per run with the isolated bridge gateway, a sidecar per seal, the runner sealed (uid:gid, `--cap-drop ALL`, the seccomp profile, no-new-privileges, read-only root, tmpfs), `--context-repo` mounts, linked-worktree git dirs mounted at the same path, cleanup on exit/INT/TERM. Tests for all of it. |
| `1b86d3bd` | `harness/sealed.py`: `sealed_container()`, the one check every sealed-lane widening was to key on (proxy: the sidecar URL and the dummy token; allowlist: a token and no base URL), with tests. |

Unreviewed partial work (subagents' local commits when T8 was stopped; kept so
nothing is lost; its tests pass on this branch, but no one has read the diffs):

| Commit | What |
| --- | --- |
| `dd25fc84` (merged in `769fb0ec`) | T8a part a: `delivery.require_hosted` also accepts a sealed container. |
| `72013f5c` (same merge) | T8a part b: `guidance.agent_env` passes `CLAUDE_CODE_OAUTH_TOKEN` inside a sealed container. |
| `92fbec07` (merged in `e47de21e`) | T8c step 1: `EGRESS_PROFILE=proxy|allowlist` entrypoint and per-seal host list for the egress sidecar (npm and rubygems registries; plus api.anthropic.com under allowlist). |

On this branch `test_issue_local_eval.py`, `test_issue_isolation_flags.py`,
`test_issue_sealed_container.py`, `test_issue_97.py` and
`test_issue_adr0012_delivery.py` passed together (366 tests, 2026-11-06).

`tools/` holds the throwaway instruments behind the measurements below:
`make_seccomp.py` (derives the profile from Docker's default), `seal_probe.py`
(the T2 probes), `mock_api.py` and `Dockerfile.mockapi` (a scripted Messages API
that lets arms run real tool calls with no token), `echo_upstream.py` (proved
the proxy's header replacement), `hook_probe.sh` (the `/proc` environ finding),
`follow_sidecar.sh` (saves a sidecar's header-free log), `Dockerfile.fixture`
(the T6 fixture layer).

Rebuild the images from the repository root:

```
docker build -f docker/eval-runner/Dockerfile --build-arg CLAUDE_CODE_VERSION=<version> -t skills-evals-runner .
docker build -t skills-evals-credproxy docker/eval-credproxy
docker build -t skills-evals-egress docker/eval-egress
```

## Decisions made (who, when)

- **S2, the credential proxy, is the seal** (Adam, 2026-11-04). He first chose
  S1 (token in the container behind an egress allowlist), then switched after
  the finding that an unsandboxed hook can read the token from the CLI's
  `/proc/<pid>/environ`. Allowlist stays only as a fallback switch
  (`EVAL_SEAL=proxy|allowlist`, default proxy).
- **Package registries through a tight squid allowlist** (captain, approved
  2026-11-04): `registry.npmjs.org`, `rubygems.org`, `index.rubygems.org`, 443
  only, for seed `deps:`/`setup:` and the fleet hooks' `npm ci`. Anthropic
  traffic only through the credential proxy.
- **Token**: `claude setup-token`, stored at `~/.config/skills-evals/oauth.env`
  on BOXY (one line, mode 600, directory 700, outside any work tree). Mounted
  read-only into the credential-proxy sidecar only (Adam's permission,
  2026-11-04). Verified by Adam with a scratch-HOME call (`result=ok`).
- **Evals paused until the sealed lane runs every eval kind** (Adam,
  2026-11-04), superseded 2026-11-06: evals resume in the cloud and this lane
  is parked.

## Measurements (BOXY, CLI 2.1.318, 2026-11-04)

**T1 image.** As first written: cold build 111 s, warm 0.7 s, 2.32 GB (the npm
package put three ~323 MB copies of the native binary in one 971 MB layer).
Final: cold 91 s, warm 0.74 s, 0.98 GB (CLI binary 338 MB, Node 125 MB, Git
26 MB after relinking and stripping, Python pins 40 MB). The seccomp profile is
Docker's default as engine 29.8.0 ships it (moby tag `docker-v29.8.0`, commit
`3ce5872b`, `vendor/github.com/moby/profiles/seccomp/default.json`, module
v0.2.3, sha256 `536529b6...`) plus one unconditional allow for clone, clone3,
mount, pivot_root, sethostname, setns, umount2 and unshare. bubblewrap fails
under the default profile and under `--cap-add SYS_ADMIN` (pivot_root is in no
default rule).

**T2 seal** (uid 1000, all capabilities dropped, the profile,
no-new-privileges, read-only root, internal network): CapEff/CapBnd 0, no Docker
or other unix socket, no host HOME, environment exactly what was passed (Docker
Desktop's "same as host" container proxy injected nothing), no Windows interop
(no `/mnt/c`, `cmd.exe` or `/init`; the kernel's WSLInterop binfmt handler,
flags `P`, still matches an MZ file but exec gets ENOENT), no internet (name
resolution fails, direct TCP unreachable), embedded DNS answers SERVFAIL for
external names, `host.docker.internal`/`gateway.docker.internal` do not resolve,
192.168.65.x unreachable, bwrap `--unshare-all` works. Control on the default
bridge: every probe opened. A plain `--internal` network still exposed the VM
side of the bridge (connection refused, so reachable); creating it with
`-o com.docker.network.bridge.gateway_mode_ipv4=isolated` removes that address.

**T3 egress allowlist (squid).** api.anthropic.com reachable (405/404 from
Cloudflare); example.com, claude.ai and statsig.anthropic.com denied
(TCP_DENIED/403). `claude -p` with the dummy: 401 after 1.9 s, no hang. Hosts
tried: api.anthropic.com only (3 CONNECTs with
`CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC=1`, 11 without).

**T4 credential proxy (nginx).** Authorization arrived and equaled the dummy;
no x-api-key; anthropic-beta `claude-code-20250219,oauth-2025-04-20,...`; POST
`/v1/messages` only; an echo upstream showed the header replaced with the
sidecar file's value whatever the client sent. With the nonessential flag off
the CLI made 8 direct calls to api.anthropic.com that bypass
`ANTHROPIC_BASE_URL`; on the internal network they fail at DNS at no cost.

**T5 harness plumbing.** local_eval in the container got through preflight,
the contamination probe (`skill_under_test_visible: false`) and workspace
setup; arms then failed at auth as expected. Fixes it took: Git 2.54+
(`git_too_old_for_fleet_hooks`), `/usr/bin/git` (`harness/workspace_git.py`
pins it), `/usr/bin/python3`, the linked-worktree git dir mount (else
`skills_evals.sha` is null), the nonessential flag on the child allow-list (14
API connections per arm without it, 3 with). With the mock API: the CLI's own
bwrap sandbox runs nested under the profile (Bash in its own PID and network
namespaces, writes outside cwd denied, the token variable absent from Bash
and from hooks). A workspace-executing scorer (`command_succeeds`,
fan-out-triage/keyword-lookalikes) matched the host check for check.

**Security finding.** The CLI scrubs `CLAUDE_CODE_OAUTH_TOKEN` from the
environment of Bash and of hooks, but a hook runs outside the sandbox beside
the CLI and can read it from the CLI's `/proc/<pid>/environ` (3 processes held
it). Under S1 that is the real token; under S2 only the dummy. This decided S2.

**T6 fixture layer.** Seed plus `npm ci` for real-work/cms-platform-761 (444
packages, 121 MB `node_modules`) on the runner image: cold 13.3 s, warm 0.76 s;
an mtime-only change does not bust the cache. But `seed_prep.install_deps` and
`fleet_hooks._npm_ci` run `npm ci` with a fresh temp cache and network on, so a
baked layer is not used today.

**T7, the first real sealed run** (S2, writing-adrs/bootstrap through
local_eval, both arms, agent claude-sonnet-5-5): rc 0, 53 s wall. with_skill
9/9, without_skill 2/9 (an earlier plain run had 9/9 and 5/9; the N=3 baseline
is 8/9 and 2.33/9). Judge skipped by the harness (objective-decided). Cost
$0.209 (with $0.152, without $0.057). Meter: one `rate_limit_event` snapshot
per arm (seven_day 0.11) through the proxy with the dummy OAuth token. Proxy
log: 10 POST `/v1/messages`, all 200, all arriving with the dummy. The
`.bashrc`/`.gitconfig`/`.mcp.json`/`.vscode` entries an arm sees in its cwd are
the CLI sandbox's mount points while a command runs, gone after it exits (the
same on the host).

**Context size and cost** (one trivial haiku turn, first-turn input tokens):
Adam's real BOXY session context 44,543 tokens ($0.0061); a sealed isolation
arm 16,538 tokens ($0.0033). Writing-adrs/bootstrap's in-place context adds
back 31 KB of deployed guidance and catalog; connectors and the personal
plugin list stay out. The cloud routine's own orchestration cost is not
measured anywhere: `usage.outer_session` is "not measured" in all of the 400
most recent routine summaries; their harness-measured cost per run was median
$0.36, mean $0.50 (192 runs).

**Memory on BOXY.** 60 stores, 4 non-empty, 22 notes (39 KB); 20 are
pointers with a `metadata.home` repository copy, 2 are `type: user`. In
practice everything durable is already in guidance, so arms lose little by
running without auto-memory.

## Remaining work, if this is ever resumed

- **T8** (harness so the sealed lane runs every eval kind; each change fails
  closed outside a sealed container):
  (a) `require_hosted` accepts `sealed_container()` (partial, unreviewed);
  (b) `guidance.agent_env` passes `CLAUDE_CODE_OAUTH_TOKEN` in a seal
  (partial, unreviewed);
  (c) runner value `container` in both `RUN_CHOICES` tables, with the ingest
  accepting container/local/subscription and refusing runner=workstation from
  a routine branch (not started);
  (d) `scripts/sealed_run.py`, the in-container entrypoint mirroring the
  routine's EVAL steps, with redaction of the token's exact, base64,
  base64url, hex and URL-encoded forms and only the routine's committed files
  in the results (not started);
  (e) wrapper: `--seal` with `EVAL_SEAL` default proxy, the registry egress
  sidecar in both seals, `--sealed-run`, `--repos-dir` with checkouts at
  `origin/main` and full history, a 30-minute hard kill, saved sidecar logs
  (only the egress profile step exists);
  (f) socat: done.
- **T9**: one in-place and one guidance fixture through `sealed_run.py` with
  the real token under S2, compared with their latest cloud routine results
  (presence, objective and judge scores, cost, wall time, meter snapshots);
  the in-place one again under S1; a dummy `ANTHROPIC_AUTH_TOKEN` variant
  against the dummy OAuth token for subscription-mode behavior.

## Open questions

- Hooked fixtures (`fleet_hooks: true`, 13 scheduled) need the ADR 0016
  network-namespace probe before they can run sealed.
- `deps:` and the fleet hooks' `npm ci` need registry egress: the squid
  allowlist above, a read-only baked cache that `install_deps` would have to
  learn to use, or a pull-through mirror sidecar.
- The routine's own session cost per run is unmeasured; recording it at the
  end of each routine run would make the cloud/BOXY cost comparison possible.
- The arms see the sandbox's dotfile mount points during commands; whether
  that changes agent behavior has not been measured.
- The long-lived token is still on BOXY at `~/.config/skills-evals/oauth.env`;
  with the lane parked, decide whether to revoke it (claude.ai settings) and
  delete the file.
- The early commits on this branch carry a model name in their
  `Co-Authored-By` trailer; published history is left as is.
- During T6 a `docker builder prune -af` cleared BOXY's whole Docker build
  cache (no images were lost).
- This session's auto-mode classifier refused the first real-token commands;
  Adam ran the auth check himself, and T7 ran after his explicit permission.
