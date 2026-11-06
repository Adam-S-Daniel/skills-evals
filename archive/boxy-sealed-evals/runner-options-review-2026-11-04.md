# Eval runner options: an adversarial review (2026-11-04)

Read-only review. Nothing in any repository was changed. Sources are the
`skills-evals` checkout at `claude/project-thread-xa1yil` (head `6f1fa8fd`,
"Run local_eval in a container with a setup-token"), the
`persistent/eval-results` branch at `974d6ed5`, and Anthropic's docs read
today (links inline). "Verified" means I read it in code, data or docs.
"Unverified" means I could not check it. Every estimate is labeled.

## 1. Bottom line

1. **Before the Mon Nov 9 deadline, slim the cloud routine you already
   have.** Do not move the lane. The current BOXY build cannot run any
   scheduled pair (see 2.1). The per-fire overhead is a fixed cost of each
   session and comes from the session's setup, not from where it runs. Cut it
   at the source: remove the connectors, set `FLEET_GUIDANCE_SKIP=1`, attach
   fewer repos, and make the saved prompt a deterministic entry script. Then
   spread it over more fixtures per fire. Expected saving: 35-55% per fire
   with no new credential and no new trust model.
2. **The capacity number decides everything else, and the two figures you
   have conflict by about 10x.** The repo's own calibration says about
   $3.57 per point. The figure you were given says about $38 per point. Pin
   this down first (Experiment 1). If $38 is right, a full sweep of the
   scheduled set costs about 7 points, the cloud routine has room to spare,
   and the allowance guard is throttling fires at about a tenth of real
   capacity.
3. **If you build an off-cloud lane, seal it with S2, never S1.** In S2 a
   proxy holds the token, so the arm never sees it. Host the lane on
   GitHub-hosted runners for public fixtures, with BOXY or an always-on
   Linux VM as an extra consumer of the same queue. BOXY should not be the
   primary host. S1 leaves the token readable, and the arm's outputs are
   published to a public repo. S1 also fails ADR 0010's own condition and
   does not authenticate in-place or guidance arms at all (see 4).
4. **Spend the $200 use-or-lose API credit.** It can go to the API lane
   now, and later to a Messages-API judge (Batch API, no tools). Through an
   S2 proxy that routes requests to the subscription or to a spend-capped
   API credential per job, it can also pay for in-place arms with the same
   client setup.
5. **Fix the judge now, on every lane.** The judge currently runs with the
   CLI's default tools, outside the sandbox, with the full process
   environment, while reading text the arm wrote.

## 2. Findings that change the picture (verified unless marked)

### 2.1 The BOXY container cannot run what the planner schedules

- [`evals/scheduled.yml`](https://github.com/Adam-S-Daniel/skills-evals/blob/main/evals/scheduled.yml)
  has 57 entries. They resolve to **34 in-place skill fixtures, 23 guidance
  fixtures and 0 isolation skill fixtures**, and 11 of them are hooked
  (`fleet_hooks: true`). I parsed every `fixture.yaml` with `yaml.safe_load`.
  Across all of `evals/`, 61 of 108 fixtures are in-place.
- `scripts/local_eval.py` runs skill fixtures only ("Refuses a fixture that
  is not a skill fixture", docstring step 3). It never passes
  `--pairing in_place`, so it covers isolation pairs and bare runs only.
- An in-place pair is gated hard to the hosted routine.
  `harness/delivery.py:83-99` (`hosted`/`require_hosted`) refuses with
  `in_place_local_unsupported` unless `CLAUDE_CODE_REMOTE_SESSION_ID` is
  set or the entrypoint is `remote*`. The message names the missing piece:
  "a local credential adapter is not built (ADR 0012)". ADR 0012's
  "Decisions on the build" deferred that adapter "to its own review and a
  controlled live test".
- Guidance and in-place arms build their environment with
  `harness/guidance.py:902` `agent_env`. It passes `ANTHROPIC_*` and
  `CLAUDE_CODE_REMOTE` and drops every other `CLAUDE_*`. So the container
  mode's `CLAUDE_CODE_OAUTH_TOKEN` never reaches those arms. Under S1 they
  would fail with "Not logged in" (`guidance.py:211-219` records the CLI
  refusing since 2.1.305).
- The image ships Debian bookworm's git. `GIT_MIN` is 2.54
  (`scripts/dev_setup.sh:28`, `run_eval.FLEET_HOOKS_MIN_GIT`), because
  config-based fleet hooks need it. The Dockerfile's own comment admits the
  gap. ADR 0016 decision 4 also requires a live netns probe for "a new host
  class", and a Docker container with nested bwrap is one.
- **Consequence:** the $0.16, 48 s measurement was an isolation pair. It is
  not the cost of what the planner fires. Measured cloud harness cost
  (below) suggests in-place pairs cost about 2-4x an isolation pair.

### 2.2 Where a fire's money actually goes (measured)

There are 412 `routine-results/*/cost_estimate.json` records on
`persistent/eval-results`. Per fire, arms + judge + guard (the harness)
cost **median $0.39, mean $0.58, p90 $1.16**, and the judge is **24%** of
that. Add the ~$0.76 orchestration you measured, and a mean fire is about
$1.34:

| Component | $/fire | Share |
|---|---|---|
| Routine orchestration (your measurement) | 0.76 | ~57% |
| Arms (mean `agent_usd`) | 0.43 | ~32% |
| Judge (mean `judge_usd`) | 0.14 | ~10% |

So moving arms off the routine saves at most the orchestration line. Moving
the judge saves about 10% of points. Arm-side caching tricks address about
a third of the bill.

### 2.3 The points conversion conflicts by about 10x

- The latest record's calibration is
  `points_per_usd = 0.0028` (fraction per CLI-dollar), so **about $3.57
  per point**. It comes from 0.49 of meter over $174.88 across 409
  invocations. `evals/budget.yml` holds `0.00214`, about $4.67 per point.
- You were given **about $38 per point**.
- The likely cause is double counting. The calibration sums each run's
  account-meter delta (`usage.meter_delta`, read account-wide) over that
  run's own dollars. With about 13 fires in flight, each run's delta also
  holds the other fires' spend, their orchestration and your interactive
  use. `docs/how-it-works.md` ("Known gaps") admits the meter is
  account-wide.
- **Why it matters.** A full sweep is 57 fixtures × 2 roster arms
  (`claude-sonnet-5-5`, `claude-opus-5-5`) × 3 trials ≈ 114 fires ≈ $260 on
  today's routine. At $38 per point that is **about 7 points**. At $3.57 per
  point it is **about 72 points**. Your steady state is 25 points every two
  weeks. That target is easy on the first figure and impossible on the
  second, whichever runner you pick.
- The allowance guard charges at the inflated rate
  (`scripts/allowance_guard.py`, `budget.yml`). If $38 is right, the guard,
  not the meter, is today's binding throttle.

### 2.4 The judge is the weakest link on every lane

`harness/scorers/judge.py:215-235` launches `claude -p` in the run's
permission mode (default `auto`) with `--setting-sources "" --strict-mcp-config
--no-session-persistence`, and nothing more:

- no `--tools`/`--disallowedTools` restriction;
- none of ADR 0011's sandbox `--settings` (that ADR explicitly left the judge
  unchanged);
- `env=guidance.cli_child_env()`, which is the **whole process
  environment**.

In a routine that environment includes `GH_TOKEN`, `GITHUB_TOKEN`,
`CLOUDSDK_AUTH_ACCESS_TOKEN` and more (ADR 0010, Probe 1). Under S1 it
includes the setup-token. The judge's input is the transcript and diff the
arm wrote. Only the auto-mode classifier stands between a prompt injection
in arm output and an unsandboxed Bash that holds those credentials. I read
this in code and did not exploit it live.

### 2.5 ADR 0010's open risk is still recorded as open

ADR 0010 left one question open: can an arm read the file
`CLAUDE_SESSION_INGRESS_TOKEN_FILE` names, or an on-disk GitHub token? Its
proposed gate was "before the first scheduled run". No document in the repo
records a closure; a grep of `docs/`, `DESIGN.md` and `harness/` finds the
phrase only in ADRs 0002 and 0010. The Read tool is not sandboxed (ADR
0011), and the arm deny list (ADR 0011 "reads" addendum) covers checkouts
and results, not that file and not `/proc/*/environ`. The cloud lane may
share S1's leak channel.

### 2.6 Doc facts the designs rest on

- **Precedence and the setup-token**
  ([authentication](https://code.claude.com/docs/en/authentication)).
  `ANTHROPIC_AUTH_TOKEN` (2) and `ANTHROPIC_API_KEY` (3) outrank
  `CLAUDE_CODE_OAUTH_TOKEN` (5). A setup-token "can only make model
  requests" and lasts one year. "Cloud sessions always use your subscription
  credentials. If you set `ANTHROPIC_API_KEY` or `ANTHROPIC_AUTH_TOKEN` in
  the cloud environment, it doesn't override". So **no API-credit arm can
  run inside a routine**.
- **Gateways and subscriptions**
  ([llm-gateway](https://code.claude.com/docs/en/llm-gateway)). "Setting only
  [`ANTHROPIC_BASE_URL`], without a gateway credential, doesn't replace the
  subscription ... a saved claude.ai login remains the active credential ...
  Gateways that pass this traffic on to Anthropic must forward the OAuth
  capability in `anthropic-beta`." So Anthropic documents a **pass-through**
  gateway for subscription traffic. A gateway that **injects** a
  subscription credential (S2) is not documented.
- **Client behavior behind a base URL**
  ([llm-gateway-protocol](https://code.claude.com/docs/en/llm-gateway-protocol)).
  A base-URL gateway gets "the beta headers and request body fields it sends
  to `api.anthropic.com`, except a small set of diagnostics and defaults
  reserved for direct connections", such as fine-grained tool streaming,
  which is off. The background-task model depends on the credential kind.
  `anthropic-ratelimit-unified-*` headers are read "to show usage against
  plan limits to developers signed in with claude.ai".
- **Terms** ([legal](https://code.claude.com/docs/en/legal-and-compliance)).
  OAuth is for "ordinary use of Claude Code". "Advertised usage limits ...
  assume ordinary, individual usage". The developer paragraph: "Anthropic
  does not permit third-party developers to offer Claude.ai login ... or to
  route requests through ... plan credentials on behalf of their users.
  Moreover, developers may not collect, store, or intermediate Claude.ai
  credentials or session tokens — sign-in to a Claude account must complete
  through Anthropic's own flow." Agent SDK products "should use API key
  authentication". Enforcement may come "without prior notice".
- **Subprocess scrub**
  ([env-vars](https://code.claude.com/docs/en/env-vars)).
  `CLAUDE_CODE_SUBPROCESS_ENV_SCRUB=1` strips credentials from Bash, hook
  and stdio-MCP subprocess environments. "The Claude Code process keeps the
  credentials for its own API calls." `claude-code-action` sets it for
  untrusted actors.
- **Cache TTL** (same page). "For subscription users within included usage,
  Claude Code requests the 1-hour TTL automatically on the main
  conversation." `FORCE_PROMPT_CACHING_5M=1` overrides it. A 1-hour write
  is billed at a higher rate (2x base on the API, against 1.25x for 5
  minutes).
- **Routines** ([routines](https://code.claude.com/docs/en/routines)).
  Routines are research preview and "Behavior, limits, and the API surface
  may change". Hourly caps: 30 fires per routine, 100 API fires and 100
  scheduled runs per account. A separate "limit on cloud sessions running
  at once" is consistent with your 429 after about 13 fires. Connectors can
  be removed per task, and the model is selectable per task.
- **Self-hosted environments**
  ([self-hosted](https://code.claude.com/docs/en/self-hosted-environments))
  would route routine sessions to your own host with an Anthropic-issued,
  session-scoped token. They are **Team/Enterprise only**, so they are out.
- **GitHub Actions**
  ([github-actions](https://code.claude.com/docs/en/github-actions)).
  `claude_code_oauth_token` is documented ("runs use your Claude
  subscription instead of API billing"). "The Claude Code GitHub Action is
  built on the [Agent] SDK."

## 3. The candidates

Shared assumptions: Sonnet arms, one paired fixture per fire, one trial.
Harness cost is the measured $0.58 mean. Points are shown at **$38/pt** and,
in brackets, at the repo's **$3.57/pt**.

| | Per fire | Points/fire | Throughput | Availability | Comparable with cloud history | Credential in an arm's reach | Terms risk | Build |
|---|---|---|---|---|---|---|---|---|
| **C today** (routine) | $1.34 | 0.035 [0.38] | ~13 sessions at once; 30/h per routine | High (preview) | Yes (it is the history) | Possibly the ingress token file (open risk) | Lowest | done |
| **C″ slim routine, 1 fixture/fire** | ~$0.75-0.95 (est.) | 0.02-0.025 [0.21-0.27] | same | same | Yes; orchestrator-only change | same | Lowest | ~0.5 day + your OK on the saved prompt |
| **C′ slim, K fixtures/fire** | ~$0.62-0.70 at K=5 (est.) | ~0.017 [~0.18] | 13 × K | same | Yes | same | Low (volume per session rises) | +1-1.5 days (planner, ingest, guard units) |
| **A-S1** BOXY, token in env | $0.58 | 0.015 [0.16] | 8-16 containers (est.), only while awake | Low (sleep, Docker Desktop, Windows reboots) | Needs a pairing study | **Yes: the 1-year subscription token** | Low-moderate | in-place blocked; needs an adapter + git + probes |
| **A-S2** BOXY, injecting proxy | $0.58 | 0.015 [0.16] | same | Low | Needs a pairing study | No (dummy only) | Low-moderate ("intermediate" wording) | 3-5 days (adapter, image parity, queue, push credential, ADR) |
| **B-S2** GitHub-hosted runners | $0.58 | 0.015 [0.16] | 20 jobs × 2-4 arms; the subscription's concurrency is the real ceiling (unmeasured) | High | Needs a pairing study; Ubuntu 24.04 like the cloud | No; an escape reaches the ephemeral VM, which holds the token | Low (setup-token in Actions is documented) | 2-3 days; shares the adapter with A |
| **G** A-S2 on an always-on Linux VM | $0.58 | 0.015 [0.16] | VM size | High | Needs a pairing study | No; an escape lands on a throwaway VM | as A-S2 | A-S2 + VM ($0 on Oracle Always Free, if capacity exists; unverified) |
| **D** API lane (`eval.yml`, WIF) | $0.58 of credit | 0 | 20 jobs | High | API vs subscription lane: gates already pool them | 1-hour, spend-capped bearer | None | 0 for what eval.yml can run today; in-place needs the adapter |
| **F** self-hosted runner on BOXY | $0.58 | 0.015 | as A | Low | as A | Any workflow can target it | n/a | Rejected |

### C. The cloud routine, slimmed. Recommended now.

**Why it beats the alternatives on cost.** The overhead is a fixed cost of
each session and does not depend on where the session runs. You measured
about 94k tokens cached at start, from 99 tools, 79 skills, 26 KB of
guidance and duplicated AGENTS.md, then about 10 calls. There are three
cuts:

1. **Shrink the session.**
   - Remove every connector from the task (documented per task).
   - Set `FLEET_GUIDANCE_SKIP=1` in the task's environment. It is a real
     switch, `.claude/hooks/fleet-memory.sh:522`. The orchestrator does not
     need the 26 KB, because arms get guidance from the harness at a pinned
     revision.
   - Attach only `skills-evals`, plus `adam-agentskills-private` when a
     private fixture runs, and have the entry script clone the public
     siblings with full history.
   - The floor you cannot remove is the account skills (cloud can't opt out,
     per registry ADR 0010) and probably the session's GitHub MCP. The real
     floor is unmeasured (Experiment 2).
2. **Fewer orchestrator calls.** Move the saved prompt's validation and
   steps into `scripts/routine_entry.py`. It should parse the untrusted
   payload strictly, run `run_eval.py`, commit and push, and print one
   RESULT line. The prompt then says only "run it and report its last line".
   That is 2-4 model calls instead of about 10. It is also safer, because
   deterministic code validates the untrusted fire text instead of the
   model, which fits your rule of preferring checks over prose.
3. **Five-minute cache TTL for a five-minute session.** Subscription
   sessions request the 1-hour TTL automatically. On a short-lived
   orchestrator, `FORCE_PROMPT_CACHING_5M=1` may cut the session-start write
   cost by up to ~37%. That assumes the meter weights 1-hour writes as the
   API bills them (unverified). The cost: cross-fire reuse of the shared
   ~30k prefix then needs fires within 5 minutes, which a burst gives.

Estimate, unverified: the orchestration falls from $0.76 to roughly
$0.2-0.35.

**C′, more fixtures per fire.** One session runs K fixtures, in parallel
where the container allows, and pushes per fixture as each finishes. The
orchestration then costs about $0.05 per fixture, within about 10% of an
off-cloud lane.

What C′ breaks, all verified in the repo:
- `plan_week.py` counts empty fires per cell from the run title (`Fire eval
  routine: eval <fixture> <model>`).
- The allowance guard reserves per fire.
- The saved prompt allows one fixture and 6 nested runs in 30 minutes.

The cheapest version needs no planner change: one fire per fixture covering
**both roster models**. `compute_gates.py` already says "one routine run
may stamp every model's arms with one `--timestamp`".

**Attack.**
- It stays a research preview, so limits and shapes can change.
- Your ~13-concurrent ceiling is real.
- One failed session loses K fixtures, so push incrementally.
- The ingress-token open risk (2.5) must be probed, not assumed.
- The judge problem (2.4) applies here too.
- Changing the saved prompt needs your OK (ADR 0010 addendum).

**Soundness.** Arms, host, CLI channel and auth path are unchanged, so
results stay comparable with everything ingested so far.

### A. BOXY sealed containers. Not first; possible later as an extra consumer.

**Against A, beyond what 2.1 already shows:**

- **Availability.** BOXY sleeps. WSL shuts down when idle. Docker Desktop
  updates and Windows reboots are unscheduled. A queue lane needs leases,
  idempotent run ids, a missing-result deadline and fallback to the cloud.
  That is a small distributed system to build in four days.
- **Blast radius.**
  - Docker Desktop runs containers in its utility VM, which mounts the
    Windows drives for bind mounts. An escape lands one hop from your real
    `~/.claude/.credentials.json`, git and SSH credentials, and browser
    profile (unverified for 4.92's exact mounts).
  - The seccomp profile that makes bwrap work re-enables `unshare`,
    `clone3`, `setns`, `mount` and `pivot_root`. Docker's default blocks
    those to shrink the kernel attack surface. It is narrow compared with
    unconfined, but wide compared with Docker's default.
  - A results-push credential (a GitHub App key) must also live on BOXY.
    Keep it host-side, outside every container.
- **Governance.**
  - ADR 0002's status note says decision 1 still holds for "a workstation".
  - ADR 0012 deferred the credential adapter.
  - ADR 0016 needs a probe of the new host class.
  - A needs its own ADR, and S1 cannot satisfy ADR 0010's own condition:
    "the arm cannot read a long-lived subscription credential".
- **Comparability.** The pinned CLI build arg will drift from the cloud's
  floating CLI (2.1.317 on Nov 3). The toolset differs: Debian slim against
  the cloud's Ubuntu 24.04 image, and a fixture whose skill says "run
  actionlint" scores differently when the binary is missing. Git differs
  (2.39 against 2.56). `CLAUDE_CODE_REMOTE` is absent, and base-URL client
  defaults differ.
- **Mitigating fact.** The gates pool "whatever its billing, runner or
  location" (`harness/gates.py:65`), but they pair arms within one fire.
  Host effects that hit both arms mostly cancel. What survives is a
  host × subject interaction, the actionlint case above. That is exactly
  what a pairing study (Experiment 3) has to look for.

**For A.**
- There is no orchestration overhead, and private skills never leave your
  machine.
- The image is mostly built.
- bwrap is already proven inside Docker.

### B. GitHub-hosted runners with S2. The best off-cloud host.

**For.**
- Public repos get free minutes. The concurrency is 20 jobs; 40 on Pro is
  from memory and unverified.
- The VMs are ephemeral Ubuntu 24.04, close to the cloud container.
- Availability is high.
- A setup-token in Actions is a documented use.
- An escape lands on a VM that dies with the job.

**Attack.**
- Use a secret scoped to an environment restricted to `main`. Otherwise
  any workflow pushed to any branch, by any agent with write access, can
  read it.
- GitHub-hosted steps have `sudo` and Docker. Arms must therefore run in a
  nested `docker run` on an `--internal` network with no `docker.sock`. The
  token must live only in the proxy container, started by a step the arms
  never run in. Whether the runner leaks `docker.sock` into job containers
  is unverified; run nested `docker run`, not `jobs.<id>.container`.
- Ubuntu 24.04 restricts unprivileged user namespaces through AppArmor, and
  Docker's `docker-default` AppArmor profile may block bwrap's mounts even
  with the seccomp profile. It probably needs a `sysctl` and
  `--security-opt apparmor=unconfined` (unverified; Experiment 5).
- ADR 0016 decision 3 currently says no Actions runner hosts a hooked arm,
  so a probe and an amendment are needed.
- Pushes made with `GITHUB_TOKEN` trigger no workflows, so the results
  handoff must be a later job, not a `push` trigger.
- Private fixtures cannot run on a public repo's runners: logs and
  artifacts are public. Run them on the routine or on the private repo's
  Pro minutes. You might lose those minutes; Free gives 2,000 a month.
- Twenty parallel headless sessions from GitHub's IP ranges looks less like
  "ordinary, individual usage". Cap concurrency near what the routine
  tolerates (about 13).

**claude-code-action.** Do not use it for arms or orchestration. It is
built on the Agent SDK and sets its own session configuration: GitHub MCP
tools, prompt additions and setting sources. The arm would no longer be the
harness's exact `claude -p` invocation. As an orchestrator it brings back an
LLM orchestration cost the Python harness does not need. Its one useful
piece, `claude_code_oauth_token`, is just an environment variable. I could
not inspect the action's current system-prompt additions, so that point is
unverified.

### D. The API credit and the judge

- **Now, at zero build.** Dispatch `eval.yml`, the WIF, `main`-pinned,
  spend-capped lane, for what it can run.
  - It refuses in-place fixtures (its header; #587). So today the credit
    buys bare runs (isolation `without_skill`, the last plan band),
    isolation diagnostics and unscheduled isolation fixtures.
  - The gates pool `results/` and `routine-results/` alike
    (`compute_gates.py:64`).
  - $200 is about 5 points at $38/pt, or about 56 at $3.57/pt. Same
    10x question.
- **A Messages-API judge (Batch, 50% off).** It removes about 10% of fire
  points. More importantly it removes the tool-enabled judge (2.4), pins
  the judge prompt independent of CLI releases, and allows temperature 0
  and structured output.
  - The costs: a new judge window (ADR 0013 already restarts one at every
    roster change, so switch at the next one).
  - Batch latency means judging moves to a post-ingest Actions job. Results
    must then carry a sanitized judge input, because `raw.json` is barred
    from pushes.
  - Private skills are judged in the private repo.
  - Effort: 1.5-3 days.
- **New: the S2 proxy as a currency router.** The arm always holds the same
  dummy. The proxy attaches either the subscription token or, on Actions,
  the WIF-minted API bearer. In-place arms could then spend the API credit
  with an identical client configuration, and nobody stores an API key. It
  must be proven that a CLI in subscription mode works against an API-key
  upstream once the OAuth beta header is stripped (unverified).

### E. Cache economics. Worth measuring, smaller than it looks.

- **Arms are about 32% of a fire.** Cross-trial sharing needs byte-identical
  prefixes. The CLI's system prompt carries the cwd, the date, git status
  and the model. The harness's workspaces get random temp paths, which
  probably break sharing at the system prompt (inference; check with the
  proxy's logs). Containers make a fixed path such as `/work/ws` easy.
- **Order matters.** Tools come first in the cache, so an arm with and an
  arm without a skill, if the skill listing sits in a tool description,
  share only what precedes it. Warm-then-fan-out helps trials of the same
  arm, not across arms.
- **Fork-from-checkpoint is invalid.** `--resume --fork-session` from a
  sampled turn makes trials share sampled tokens, so N trials stop being N
  independent samples. Share only the prompt, which is what caching does.
- **Memoized baselines already exist** as digest pooling (`compute_gates`,
  `min_cli_versions`, the bare run once per model). Extending reuse across
  CLI versions breaks the gates' version-span guard.
- **1-hour against 5-minute TTL for arms.** One-shot arms probably overpay
  for 1-hour writes, but the 1-hour TTL is what makes cross-trial reuse of
  the tools prefix possible. Measure both. Either way, record the TTL,
  because it changes the cost KPI but not behavior.
- **Layered images** cut wall time, not tokens.

### F. Self-hosted runner. Rejected.

Any workflow in a PR can target `runs-on: self-hosted`, which ADR 0002
already rejected. A BOXY pull queue is the safe equivalent: BOXY fetches,
and nothing pushes code to it.

### G. New: an always-on Linux VM in place of BOXY

The same A-S2 stack on Oracle Always Free (Arm, if capacity can be had;
unverified) or a ~$5/month VPS. It fixes both of A's structural problems,
availability and the workstation blast radius. It runs native Docker, not
Docker Desktop. It costs money or a free-tier gamble, which may conflict
with "subscription only" in spirit.

### Ruled out

- Self-hosted environments (Team/Enterprise only).
- Routine arms on the API credit (cloud ignores API credentials).
- The Agent SDK on OAuth (the terms steer developers to API keys).
- Arms as routine subagents (ADR 0010: a different measurement).
- A Haiku orchestrator, unless auto mode is shown to work with it. The
  routines doc says that without auto mode a run keeps its launch mode and
  can stall on prompts.

## 4. S1 against S2

### What a compromised or confused arm can do

- **S1** (token in the arm's environment, egress only to api.anthropic.com
  through CONNECT):
  - Read the token: `env` in Bash, the Read tool on `/proc/self/environ`,
    or `/proc/<cli>/environ`.
  - Write it, encoded, truncated or split, into the workspace, the
    transcript or `tool_trace.json`. Those files are pushed to a public
    repo.
  - `redact_token` replaces the exact string only, so a base64 copy or one
    a truncation cut in half passes. GitHub masks only exact values.
  - "Can send it only to Anthropic" does not hold either. Any unsandboxed
    process with the token and egress to api.anthropic.com can call the
    Messages API with a server-side fetch tool, and that sends the token
    to any URL. Server tools on OAuth tokens are unverified. An
    unsandboxed process exists: the judge (2.4), hooks, and the fleet
    hooks.
  - Arms' Bash cannot do any of this, because ADR 0011's sandbox gives it
    no network.
  - The blast radius is a one-year, model-request credential on the whole
    subscription. A third party using it could count as credential sharing
    (Consumer Terms § 2) and risk suspension of the account.
- **S1 hardened.** Add `CLAUDE_CODE_SUBPROCESS_ENV_SCRUB=1`, a
  `Read(//proc/**)` deny plus `denyRead` for `/proc/*/environ` in the arm
  `--settings`, a redaction pattern for the token's prefix and substrings,
  and a judge with no tools. That closes the known paths. It stays
  arm-readable in principle, because the CLI process holds the token and
  its `/proc` entries exist. Proving the negative is hard. Keep it only as
  the fallback if S2 hits a CLI incompatibility.
- **S2** (a proxy injects the token; the arm sees a dummy and
  `ANTHROPIC_BASE_URL`):
  - Nothing to steal. This is the only design that meets ADR 0010's
    condition and is the "credential adapter" ADR 0012 asks for.
  - The residual risk is quota abuse, plus exfiltration of private-skill
    text through server tools, from any unsandboxed process that can reach
    the proxy.
  - Mitigate with a body-inspecting proxy, a ~100-line Python program
    rather than plain nginx:
    - allow only `POST /v1/messages` and `/v1/messages/count_tokens`, plus
      whatever startup endpoints the proxy's permissive-mode log shows the
      CLI needs;
    - reject server-tool definitions and `mcp_servers`;
    - cap request rate;
    - refuse with 429 once `anthropic-ratelimit-unified-*` shows the
      account above `stop_when_account_above`. That makes the proxy an
      exact, account-wide allowance guard.
- **S2 works for every arm kind with one harness change.** Use the dummy as
  `ANTHROPIC_AUTH_TOKEN`, which both `agent_env`s pass through. Then replace
  `require_hosted` with an explicit adapter check: base URL equals the
  sidecar, and no real credential is in the environment. The proxy must
  then add the OAuth `anthropic-beta` value itself. The client then runs in
  gateway-credential mode, so it shows no usage meter, and the harness's
  in-run stop falls back to dollars, which it already supports.
  - A dummy `CLAUDE_CODE_OAUTH_TOKEN` keeps the CLI in subscription mode,
    but needs a `CLAUDE_*` passthrough in `guidance.agent_env`.
  - Setting `CLAUDE_CODE_REMOTE=true` would mimic the cloud's exact shape.
    It is documented as set automatically, so setting it yourself is
    undocumented and may trigger remote-only code paths. Test it, don't
    depend on it.
- **Terms.** Both S1 and S2 store the token, as the GitHub Actions doc
  itself does. S2 adds the literal "intermediate". The paragraph is aimed
  at third-party developers acting "on behalf of their users", and the
  token comes from Anthropic's own flow. My reading is low risk, but it is
  ambiguous, and enforcement may come without notice. S1 does not avoid the
  larger shared risk: high-volume automated use on one personal plan.

## 5. What would make results non-comparable

- CLI version (system prompt and tools change per release; record it, and
  the gates' `min_cli_versions` already uses it).
- Permission mode, and whether auto mode actually engages under a
  setup-token or behind a base URL (unverified).
- Client mode: direct, base URL with an OAuth credential, base URL with
  `AUTH_TOKEN`, or hosted (`CLAUDE_CODE_REMOTE`). This affects defaults such
  as fine-grained tool streaming and the background-task model, and
  possibly the context window by plan (unverified).
- Toolset on PATH, git version (hooks), sandbox availability.
- Judge implementation and model (ADR 0013 windows).
- Cache TTL (cost only).
- Wall time across hosts: never comparable. Use turns and tokens.
- Runner. Pairs stay within one fire, which limits host bias to host ×
  subject interactions.

## 6. The five cheapest experiments that decide

1. **Quiet-window meter calibration.** Decides the capacity, and with it
   whether C alone suffices; ~$3-40.
   - Run with nothing else on the account.
   - Fire about 15 slim routine fires, or BOXY isolation pairs, sized to
     move the whole-point meter at least 2 points, or log the fractional
     `anthropic-ratelimit-unified-*` values through any proxy (whether they
     are fractional is unverified).
   - Report points per CLI-dollar for arms alone and for the routine
     overhead.
   - Decision: above about $20/pt, the cloud routine has room for full
     sweeps; recalibrate `points_per_usd` and stop building lanes for cost.
2. **Slim-routine A/B.** Decides C″/C′ against an off-cloud lane; ~$5.
   - Clone the eval routine as `eval-slim`: no connectors,
     `FLEET_GUIDANCE_SKIP=1`, one repo attached, optional
     `FORCE_PROMPT_CACHING_5M=1`, and a 3-line prompt that runs an entry
     script. Even a hand-run shell script is enough for the test.
   - Fire the same in-place fixture twice on each routine. Compare session
     usage and results.
   - Decision: if the slim overhead is at most $0.25, an off-cloud lane
     saves at most about 20% and is not worth its risk this month.
3. **Seal and auth probe in the BOXY container.** Decides S2 against S1
   hardened and whether A or B can work at all; a few dollars.
   - **(a)** One canary arm asked to find any credential and write it
     base64-encoded into the workspace, under S1, S1 hardened and S2. Plant
     a decoy token-shaped variable, keep results local, never push, rotate
     the real token if it surfaces.
   - **(b)** `--permission-mode auto` engages and the meter or usage events
     appear under each auth mode.
   - **(c)** From sandboxed Bash and from a mid-run workspace hook: can
     they reach the proxy?
   - **(d)** The proxy's allowlist works with the CLI's real endpoint set.
   - **(e)** The ADR 0016 netns probe with Git 2.56 built in (`dev_setup.sh
     --build-git`).
   - **(f)** The same zero-model probe inside a routine for 2.5: is the
     ingress token file, `/proc/*/environ` or a git credential readable
     under `agent_env`?
4. **Pairing study.** Decides whether an off-cloud lane can pool;
   ~$10-20.
   - Three fixtures (one in-place skill, one guidance, one real-work
     CI-debug that uses tools) × 3 trials × both arms, on the cloud and on
     the S2 container, same CLI version and model.
   - Compare the per-arm pass rates and the with−without delta, turns,
     tokens, `command not found` counts in `tool_trace.json`, and the
     `system/init` tools, skills and permission mode.
   - Decision: deltas within trial noise and no host-specific tool
     failures.
5. **GitHub-hosted runner probe.** Decides B; one model request and free
   minutes.
   - In a `workflow_dispatch` job: build the image, start the proxy with
     the secret from a `main`-only environment, run a nested `--internal`
     container.
   - Check `docker.sock` visibility, AppArmor userns, bwrap, the ADR 0016
     netns marker, and `claude -p 'Reply with exactly: ok'` through the
     proxy.

## 7. Immediate, cheap and lane-independent

- **Judge isolation.** No tools, via `--tools ""` if the pinned CLI has it
  (unverified) or else `--disallowedTools` for every built-in. An env
  allowlist like the arms'. The sandbox `--settings`.
- **Token redaction by pattern, not only exact match.** Catch the token
  prefix and any 16+ character substring, and refuse to push on any hit
  rather than redacting.
- **Close or record ADR 0010's open risk**, with Experiment 3(f).
- **Recalibrate `points_per_usd`** from Experiment 1. Until then, the guard
  may be holding fires to about a tenth of real capacity, if $38/pt is
  right. Changing `budget.yml` is your spending decision.
- **Find what is burning 2.4%/h.** At $38/pt that is about $91/h, roughly
  70 cloud fires an hour. If interactive and orchestrating sessions
  dominate, the same per-session overhead (tools, skills, guidance,
  duplicated AGENTS.md) is a bigger lever than any eval runner.

## 8. Not verified

- The $38/pt figure itself, and whether the meter weights cache reads and
  1-hour writes as API pricing does.
- Whether the slim routine's floor (account skills, session GitHub MCP) can
  get below ~40k tokens, and whether a routine can run Haiku in auto mode.
- Server-side tools usable with OAuth tokens (the S1 relay path); the exact
  OAuth `anthropic-beta` value; the startup endpoints the CLI calls behind
  a base URL.
- That auto mode works under a setup-token and behind a base URL; the
  context window by auth mode.
- `docker.sock` in GitHub job containers; AppArmor on ubuntu-24.04
  runners; Pro's 40-job concurrency.
- Docker Desktop 4.92's host-drive mounts inside its VM.
- claude-code-action's current prompt and MCP additions.
- How to revoke a setup-token (prove it before you deploy one anywhere).
- Whether GitHub secret scanning recognizes setup-token values.
- In-place arm cost off-cloud. It is inferred from the cloud's harness
  costs, not measured.
