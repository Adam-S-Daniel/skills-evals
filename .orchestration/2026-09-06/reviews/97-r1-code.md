NOT CLEAN — no blockers and every issue item is implemented with teeth, but five should-fix items stand, the sharpest being that `test_delivery_refuses_the_real_config_dir` hands the operator's REAL `~/.claude` to the real delivery function with only the production guard in between (I tripped it, and it destroyed `/root/.claude/CLAUDE.md`).

Round-1 code review — `claude/skills-evals-97` @ `34ab8fcc5c9a41d9faf8745d4b935972e97f1d8b`
Issue [#97](https://github.com/Adam-S-Daniel/skills-evals/issues/97) · epic [#95](https://github.com/Adam-S-Daniel/skills-evals/issues/95) · parent [_agent-guidance#118](https://github.com/Adam-S-Daniel/_agent-guidance/issues/118) · base `origin/main` = `c05d7de`

Work dir `$SP/rev97a-code` verified against `git show 34ab8fc:<path>` for all seven named files — all OK.

---

## 1. Verifiers

| Verifier | Result | Skips (every reason) |
|---|---|---|
| `python3 test/run_tests.py` (sibling `_agent-guidance` present) | **438 tests, exit 0** | 2 — `pypdf not installed` ×2 (`TestIssue82`) |
| `python3 test/run_tests.py` (no sibling) | 438 tests, exit 0 | 14 — 2 `pypdf not installed`; 1 `no agentskills checkout … skipping the cross-repo registries.yml agreement check`; **11 guidance**: 8 `no fleet-memory.sh under …_agent-guidance — skipping the real-hook delivery checks`, 1 `…skipping the cross-repo extent/bytes agreement check`, 1 `…skipping the end-to-end delivery-canary run`, 1 `…skipping the section-id agreement check` |
| `python3 test/test_propagation.py` | **164 tests, exit 0** | 1 — `no agentskills checkout at /root/repos/agentskills` |

Every skip prints its reason; none is silent. The 11 guidance skips are exactly the real-hook tests, and `ci.yml` now checks out `_agent-guidance` so they run in CI — pinned by `test_ci_checks_out_agent_guidance_so_the_hook_tests_actually_run` (`test/issues/test_issue_97.py:1177`), which goes red if the checkout is removed.

**Fixture identity — a harness change must leave every skill fixture byte-identical.** All 7 committed fixtures, `--arm objective-only`, head vs `$SP/mainx2`:

| Fixture | head exit | main exit | stdout |
|---|---|---|---|
| `evals/github-actions-sha-pinning` | 1 | 1 | **identical** |
| `evals/guidance-bridge-canary` | 2 | 2 | **identical** |
| `evals/post-failure-comment` | 1 | 1 | **identical** |
| `evals/propagation` | 2 | 2 | **identical** |
| `evals/rename-pdfs` | 1 | 1 | **identical** |
| `evals/windows-elevation-from-wsl` | 1 | 1 | **identical** |
| `evals/workflow-path-audit` | 1 | 1 | **identical** |
| `evals/guidance/_delivery` | 0 | — | new (see nit N6) |

No `evals/adam-writing-style` exists on either side.

---

## 2. Per-item verdicts

Hollowness base: head's `test/run_tests.py` + `test/issues/` + `test/fake-claude` dropped onto a copy of `$SP/mainx2`. Dropped bare, the module cannot import (`ModuleNotFoundError: No module named 'guidance'`) → 1 synthetic ERROR, exit 1 — which is also the live proof that a broken issue file **fails** the run. Adding only the wholly-new `harness/guidance.py` and leaving everything else at main gives the useful reading: **52 of 59 red** (26 failures + 26 errors). The 7 that stay green are the pure payload/extent/env/hook tests, which is correct — they test the new module I copied in.

Mutations below are applied to a scratch copy (never `$SP/rev97a-code`) and scored by the **full 438-test suite**.

| # | Item | Verdict | Pin (file:line) | Hollow? | Mutation → result |
|---|---|---|---|---|---|
| 1 | Schema: `subject: guidance`, `section:`, arms with `mode:`, default `section`/`none`, `ablation:` | **PASS** | `run_eval.py:1082`, `:660` (`_validate_arm_entry`), `:709` (`guidance_arms`); tests `:1077`,`:1082`,`:1117` | RED | `subject == "guidance-DISABLED"` → **16 red** |
| 2 | Payload assembly, pure, real markdown parse | **PASS** | `guidance.py:193` (`h2_extents`), `:291` (`assemble`) | RED | regex line-scan for `## ` → **7 red** (`test_a_fenced_h2_never_ends_an_extent`); drop intro prepend → **3 red** |
| 3 | Delivery through the real `fleet-memory.sh`; `user,project` vs `project` | **PASS** | `guidance.py:354` (`deliver`), `:74` (`SETTING_SOURCES`) | RED | write payload directly instead of running the hook → **5 red**; `SETTING_SOURCES["user"]="project"` → **8 red** |
| 4 | Per-arm guard → INCONCLUSIVE, no score, exit 2 | **PASS** | `guidance.py:439` (`run_guard`), `run_eval.py:1015`; tests `:607`,`:632`,`:657` | RED | `return 0` on inconclusive → **7 red**; score anyway → **7 red** |
| 5 | Environment allowlist | **PASS (with S4)** | `guidance.py:400` (`agent_env`), `:97` (`PASSTHROUGH`) | RED | `env = dict(os.environ)` → **2 red**. *But widening `PASSTHROUGH` → **0 red** — see S4* |
| 6 | Results `guidance/<id>`, summary fields, report header, `make_badge` | **PASS** | `run_eval.py:949`, `:467` (`_write_summary`), `:815` (`_render_guidance_report`); `make_badge.py:65-100` | RED | `key = section` → **14 red**; revert `make_badge.py` → **9 red** |
| 7 | `evals/guidance/_delivery`, five arms | **PASS** | `evals/guidance/_delivery/fixture.yaml`; tests `:841`,`:859`,`:870`,`:1204` | RED | drop one arm → **5 red**; `timeout_s: 1200` → **3 red** |
| 8 | `eval.yml` `_agent-guidance` checkout + security header | **PASS** | `eval.yml:176-186`, header `:31-40` | RED | delete checkout → **3 red**; delete header clause → **3 red** |
| 9 | README + DESIGN "Guidance subject" | **PASS** | `README.md` §Guidance subject, `DESIGN.md` §Guidance subject | RED | revert both to main → **3 red** |
| 10 | `judge.score_fixture` (pairwise, PR #131) | **CORRECTLY LEFT** | — | n/a | `harness/scorers/` is **untouched** by the branch (`git diff --stat c05d7de..34ab8fc -- harness/scorers/` empty); `score_fixture` appears nowhere in the tree. **Nothing ported from #131.** |
| M | Merge condition: validated `fixture` dispatch input | **PASS** | `eval.yml:114-122` (input), `:220-243` (validation), test `:931`,`:946`,`:962`,`:997`,`:1007`,`:1015` | RED | `${{ inputs.fixture }}` in the `run:` → **25 red**; move validation after OIDC → **3 red** |
| D | Per-issue test discovery | **PASS (with S3)** | `test/run_tests.py:6063-6098` | RED (import error) | disable `loader.discover` → **0 red** — see S3 |

Additional error paths, all driven through the production CLI (`harness/run_eval.py` + `test/fake-claude`), all exit 2 with a named message and **no traceback**:

- unknown section id → names the manifest path *and* lists all 28 known ids
- missing checkout → names `--guidance`, `$AGENT_GUIDANCE_DIR`, the sibling
- checkout without the hook (mid-run) → names `fleet-memory.sh`
- unknown arm key → `arm 'x' has unknown key(s) ['objective_check']`
- unknown subject → `expected 'skill' or 'guidance'`
- skill fixture given a guidance arm name → lists the four skill arms

The loosening of `EvalWorkflowSecurityHeaderTests`' `registry_checkouts` (`run_tests.py:1375-1387`) keeps its teeth: dropping `--registry cms-platform=…` → red (`test_registry_flags_match_registries_yml_and_checkout_paths`), and adding an arbitrary un-headered checkout → red (`test_header_names_every_checkout_and_the_automated_lane_clause`).

---

## 3. The guidance subject in detail

**Extent arithmetic vs `_agent-guidance`'s `scripts/check-guidance-coverage.js`** — all 28 manifest rows, `bytes` column vs what `guidance.py` computes:

| id | file | manifest | chars | utf-8 bytes | |
|---|---|---:|---:|---:|---|
| working-in-these-repos | base.md | 1366 | 1350 | 1366 | OK |
| anything-you-name-gets-its-link | base.md | 2681 | 2663 | 2681 | OK |
| finding-your-unknowns | base.md | 1520 | 1512 | 1520 | OK |
| workstation-layout | base.md | 653 | 649 | 653 | OK |
| sessions-get-cut-off | base.md | 1152 | 1144 | 1152 | OK |
| security | base.md | 493 | 491 | 493 | OK |
| data-exposure-in-ci | base.md | 2247 | 2233 | 2247 | OK |
| network-allowlists | base.md | 1223 | 1217 | 1223 | OK |
| automation-vs-branch-protection | base.md | 2483 | 2465 | 2483 | OK |
| two-github-connectors | base.md | 4055 | 4033 | 4055 | OK |
| github-404-means-not-authorized | base.md | 1787 | 1777 | 1787 | OK |
| fleet-spans-two-owners | base.md | 2987 | 2971 | 2987 | OK |
| watch-finished-is-not-ci-passed | base.md | 3988 | 3970 | 3988 | OK |
| git-push-does-not-mean-commit-exists | base.md | 3026 | 3004 | 3026 | OK |
| dependency-updates | base.md | 1086 | 1082 | 1086 | OK |
| name-becomes-scanner-data | base.md | 3292 | 3280 | 3292 | OK |
| pinning-github-actions | base.md | 3963 | 3941 | 3963 | OK |
| subagent-delegation | base.md | 7761 | 7727 | 7761 | OK |
| skills-ecosystem | base.md | 2612 | 2600 | 2612 | OK |
| two-setup-gaps | base.md | 5615 | 5575 | 5615 | OK |
| git-practices | base.md | 1393 | 1389 | 1393 | OK |
| section-docker | sections/docker.md | 604 | 602 | 604 | OK |
| section-dotnet | sections/dotnet.md | 662 | 660 | 662 | OK |
| section-go | sections/go.md | 553 | 549 | 553 | OK |
| section-javascript | sections/javascript.md | 495 | 493 | 495 | OK |
| section-python | sections/python.md | 544 | 542 | 544 | OK |
| section-rust | sections/rust.md | 555 | 555 | 555 | OK |
| section-typescript | sections/typescript.md | 526 | 526 | 526 | OK |

**28/28 agree.** 26 of 28 have chars ≠ bytes, so `test_extents_agree_with_the_real_manifests_generated_bytes` (`:370`) — which encodes before comparing — genuinely discriminates rather than passing by luck. The end-to-end run confirms the identity against the *real* guidance: `full` = 55988 B, `full-minus-section` = 55495 B, difference **493** = exactly `security`'s manifest bytes.

**Extent edge cases**, probed directly against `guidance.h2_extents`:

| Case | Result |
|---|---|
| `## ` inside a fenced block | not a heading; content after the fence stays in the extent ✓ |
| heading inside an HTML block (blank line closes it) | treated as a heading — CommonMark-correct ✓ |
| heading inside a *tight* HTML block | not a heading ✓ |
| CRLF line endings | correct extents; char offsets stay aligned ✓ |
| setext `Alpha\n-----` | recognised as h2; extent starts at the text line ✓ |
| last section, file ends with `\n` | `end` = EOF, no phantom-line overcount ✓ |
| last section, **no** trailing `\n` | ✓ |
| `## Closed Form ##`, leading-indent ATX | heading text `Closed Form`; indented heading found ✓ |
| lone `\r` (old-Mac) | **degrades** — see nit N1 |

**Delivery** is the real hook: `deliver()` (`guidance.py:354`) runs `bash <checkout>/.claude/hooks/fleet-memory.sh` with `FLEET_GUIDANCE_PAYLOAD` and `CLAUDE_CONFIG_DIR=<per-arm scratch>`. The delivered file carries the hook's own `BEGIN/END FLEET GUIDANCE` marks and `fleet-guidance-version:` line, so it is the real output, not an imitation. `mode: none` runs nothing and leaves no `CLAUDE.md`.

**Env allowlist — measured**, by running the real fixture through `harness/run_eval.py` under `env -i` with a poisoned environment and logging `os.environ` in every child (10 invocations = 5 arms × [guard probe + agent]). Exactly these reached the agent:

```
ANTHROPIC_AUTH_TOKEN   ANTHROPIC_BASE_URL   CLAUDE_CONFIG_DIR
HOME   LANG   NODE_PATH   PATH   SHELL   TMPDIR   USER   WORKSPACE
FAKE_CLAUDE_MODE   FAKE_CLAUDE_ARGV_LOG      <- from the fixture's own env:
```

Scrubbed, every one: `AWS_SECRET_ACCESS_KEY`, `GITHUB_TOKEN`, `GH_TOKEN`, `SSH_AUTH_SOCK`, `HOSTNAME`, `LOGNAME`, `CLAUDE_CODE_REMOTE_SESSION_ID`, `MY_LAPTOP_NAME`. **Nothing credential-shaped or host-identifying leaks.** (`USER` and `SHELL` are passed and are not in the issue's item-5 list; benign — `USER` is `runner` in CI — and noted only as context for S4.)

**`--setting-sources`, measured from the child's own argv**: `user,project` on all 10 guidance invocations (guard *and* agent); `project` on both arms of a skill fixture.

**The guard, driven by a lying fake CLI** through the production entry point:

| Scenario | Result |
|---|---|
| honest CLI | exit **0** |
| `guidance_blind` (delivered, probe never sees it) | exit **2**, all four `with_*` arms INCONCLUSIVE, message names expected/observed |
| contaminated control (an ambient "real `~/.claude`" carrying this run's token) | exit **2**, `without_guidance` INCONCLUSIVE with `guard_miss` |

In the contaminated run the failed arm's summary has `objective_checks: null` and `judge: null` — **no score written** — while the four healthy arms scored normally. Results key is `guidance/security`; summaries carry `subject`, `section`, `mode`, `bytes` (55988 / 55495 / 3426 / 1098 / 0), `delivery: user`, and the full `guard` block. `report.md`'s header names the mode pair. Nothing in `results/` (summaries, `report.md`, `transcripts/raw.json`) contains the delivered corpus — only the agent's reply — and `guard.reply` is capped at 500 chars, so a failed-run artifact cannot exfiltrate the guidance.

**The canary fixture** (`evals/guidance/_delivery/fixture.yaml`): one arm per mode; prompt names no rule, section or manifest row; no seed and no domains at all (so `example.com`/`.net` is vacuously satisfied); checks are `transcript_matches` on `$MAGIC_TOKEN` — purely lexical. Budget: 5 arms × (120 s agent + 120 s guard) = 1200 s against `eval.yml`'s 2700 s job timeout, and `test_the_delivery_canary_fits_inside_the_workflow_job_timeout` (`:1204`) reads **both** numbers from their real sources with a 0.75 headroom factor, so the two cannot drift apart in either direction. **`--arm both` = every declared arm** for a guidance fixture (5 measured) and **exactly two** for a skill fixture (measured).

---

## 4. `eval.yml` / `ci.yml` against the security header

| Header rule | Verdict |
|---|---|
| Every `uses:` a bare 40-hex SHA, no trailing comment | **PASS** — all 8 in `eval.yml`, all 3 in `ci.yml`, checked by regex `^[^@\s]+@[0-9a-f]{40}$` |
| New checkout reuses the file's existing `actions/checkout` pin | **PASS** — `3d3c42e5aac5ba805825da76410c181273ba90b1`, identical to the other four |
| No `${{ }}` inside any `run:` block | **PASS** — zero, both files (mutation → 25 red) |
| Triggers `schedule` + `workflow_dispatch` only; no `pull_request` in `eval.yml` | **PASS** — the only `pull_request` occurrences are the header's own "NEVER add pull_request" prohibition |
| `permissions` byte-unchanged | **PASS** — `contents: write`, `id-token: write`, diff empty |
| `concurrency` byte-unchanged | **PASS** — `group: real-eval`, `cancel-in-progress: false`, diff empty |
| New `_agent-guidance` checkout `persist-credentials: false` | **PASS** — `eval.yml:185`, `ci.yml:93` |
| Push auth step-local to the final commit step | **PASS** — `GITHUB_TOKEN` appears only in that step's `env:` (`:322`) and its own `run:` (`:356`) |
| Validation ordered BEFORE the OIDC exchange | **PASS** — step 10 (`:220`) vs step 11 (`:245`); mutation moving it after → red |
| Eval step reads the fixture from `$RUNNER_TEMP/eval-fixture` | **PASS** — `:294`, not from the event a second time |
| `--guidance ../_agent-guidance` harmless for a skill fixture | **PASS** — proven below |
| Badge / results key, `[skip ci]` commit message | **PASS** — badge stays `workflow-path-audit` (documented: the published badge is the reference A/B's); commit message is `eval: $(cat "$RUNNER_TEMP/eval-key") run + badge [skip ci]` |
| `_agent-guidance` is not a registry | **PASS** — gets `--guidance`, never `--registry`; asserted at `:1038` |
| Header names the new trust boundary | **PASS** — "write access to `_agent-guidance`'s default branch is therefore equivalent to key access here" |
| `markdown-it-py` pinned exact in both workflows | **PASS** — `markdown-it-py==4.2.0` in `eval.yml:207` and `ci.yml:101`; installed version matches. *(Publish date not verifiable offline — flagging for the orchestrator only.)* |

The yaml-parsing test pins all of it: I mutated each invariant separately and every one goes red — interpolated input (25), validation-after-OIDC (3), checkout removed (3), header clause removed (3), registry flag dropped (3), un-headered checkout added (3).

**Skill-fixture identity with `--guidance`** — `evals/workflow-path-audit --arm both --no-judge`, once with and once without `--guidance $SP/_agent-guidance`:

| Artifact | Result |
|---|---|
| stdout | **identical** (`diff` clean) |
| `with_skill/summary.json` | **identical** (timestamps normalised) |
| `without_skill/summary.json` | **identical** |
| `report.md` | **identical** |
| arms produced | exactly `with_skill` + `without_skill`, both runs |

---

## 5. Findings

### Blockers
**None.**

### Should-fix

**S1 — a test that arms the weapon it guards against.** `test/issues/test_issue_97.py:468`, `test_delivery_refuses_the_real_config_dir`, passes the operator's **real** `~/.claude` as `dest_dir` into the real `guidance.deliver(..., payload="anything\n")`. Nothing but the production refusal at `harness/guidance.py:366` stands between the test and user memory; `assertRaises` observes the exception, it does not prevent the write.

Measured, by the standard revert-the-fix probe (delete `_refuse_real_config_dir(dest_dir, home)` and run the suite): `/root/.claude/CLAUDE.md` went `935c291f2efb1ff55a463bccfde55e6a` → `d4ebe18523a07b5de5d78a27f6c69a6a`, truncated to 154 bytes containing only a marked block whose body is `anything` and whose version line is `fleet-guidance-version: ce32b18a` = `sha256("anything\n")[:8]` — content-level proof of which test wrote it. **Head as committed is safe**: a full 438-test run leaves the file byte-unchanged, which is why this is should-fix and not a blocker. But the ordinary act of reviewing or refactoring that guard destroys the reviewer's user memory, which is not a cost a test should carry.
*Fix:* resolve the refusal against a patched home (`mock.patch.object(guidance.os.path, "expanduser", …)` onto a temp dir) so the same branch executes with nothing real in reach, or assert on `_refuse_real_config_dir` directly — it is a pure function — instead of through `deliver`.

**S2 — the guardrail test does not have the scope the issue asks for.** The issue says "Never write to the real `~/.claude/CLAUDE.md`; the test asserts it." `test_a_whole_run_never_touches_the_real_user_memory` (`:743`) snapshots `before`/`after` around **only its own `_run_main` call**, so in the S1 run it stayed **green** while the real file had already been destroyed by another test in the same suite. Measured: m20's entire red list was `test_delivery_refuses_the_real_config_dir` plus the discovery cascade — the file-integrity test never fired.
*Fix:* take the snapshot in `setUpClass`/`tearDownClass` (or `setUpModule`) so it spans the suite.

**S3 — nothing pins the per-issue discovery, and a narrowed run reports a false green.** `test/run_tests.py:6080`. Disabling `suite.addTests(loader.discover(...))` leaves the suite at `Ran 379 tests … OK`, **exit 0, zero red** — a silent 59-test drop, because both discovery pin tests live *inside* the module that stops being discovered. The same shape is reachable without editing anything: `main()` (`:6089`) routes any argv to `unittest.main(module=…)`, so `python3 test/run_tests.py -v` runs **379** and prints `OK` with nothing on screen saying 59 tests were not run. (`python3 test/run_tests.py TestIssue97` at least fails loudly.) This is the fleet's "the DENOMINATOR is the part that lies" defect, in its false-green direction.
*Fix:* a class in `run_tests.py` **itself** asserting that `build_suite()` loaded a module for every `DISCOVERY_DIR.glob(DISCOVERY_PATTERN)` file; and print a one-line notice when argv narrows the run.

**S4 — the env allowlist is unpinned, only its negatives are tested.** `harness/guidance.py:97`. `test_agent_env_is_an_allowlist_that_still_carries_anthropic_vars` (`:485`) asserts that two named ambient variables are absent — it never asserts what `PASSTHROUGH` *is*. Measured: adding `GITHUB_TOKEN`, `AWS_SECRET_ACCESS_KEY`, `SSH_AUTH_SOCK`, `HOSTNAME`, `CLAUDE_CODE_REMOTE_SESSION_ID` to `PASSTHROUGH` passes **all 438 tests green**, and I then confirmed by argv-logging that all five reach a `bypassPermissions` agent in the key-bearing lane. The asymmetry is the tell: `EXTRA_PASSTHROUGH` *is* pinned exactly (`test_extra_passthrough_is_empty_in_production`, `:514`) while the allowlist it modifies is not.
*Fix:* one `assertEqual(guidance.PASSTHROUGH, (...))`.

**S5 — `grep -Fxq` behind a pipe under `pipefail`** (the item flagged for a ruling). `.github/workflows/eval.yml:232`: `printf '%s\n' "$committed" | grep -Fxq -- "$fixture"`. **Ruling: should-fix, not a nit — and not a blocker.** Measured, 20 trials per size:

| committed list | `printf … \| grep -Fxq` | `grep -Fxq -- "$f" <<<"$committed"` |
|---|---|---|
| 8 entries (111 B) | 20/20 accept — safe | 20/20 accept |
| 5000 entries (70 KB) | **19/20 — one false rejection** | 20/20 accept |
| 20000 entries (280 KB) | **0/20 — always rejects** | 20/20 accept |

Today's list is **209 B, 313× under the 64 KiB pipe buffer**, so it cannot fire, and when it does it fails **closed** (a valid fixture rejected, no credential minted, nothing spent) — hence not a blocker. But it is the fleet's own named trap reproduced in the fleet's own evals repo, and the fix is one line: `grep -Fxq -- "$fixture" <<<"$committed"`.

### Nits / record-only

- **N1** `harness/guidance.py:210` — `text.split("\n")` while markdown-it normalises a lone `\r` to a newline, so an old-Mac-line-ending guidance file yields empty extents; a `section` arm would then deliver only the magic-word paragraph and still **pass** its guard. Measured: both extents collapse to `start=end=32`. Unreachable through `_agent-guidance`'s LF pipeline, and `check-guidance-coverage.js:95` carries the identical `src.split("\n")` — so fixing it here alone would break the byte agreement the module deliberately preserves. A one-line `if not payload.strip(): raise GuidanceError(...)` in `assemble` would close it locally without touching the arithmetic.
- **N2** `harness/guidance.py:204` — the docstring says the arithmetic is "the same as `check-guidance-coverage.js`". The line-start arithmetic and the phantom-line handling do match; the **unit** does not (the JS uses `Buffer.byteLength`, this returns character offsets). Both uses are correct as written and the cross-repo test encodes before comparing — worth one clarifying clause so the next reader does not "fix" it.
- **N3** `.github/workflows/eval.yml:144` — `timeout-minutes: 45 # 2 arms x 10 min agent budget + judges + setup`. The comment is stale for a 5-arm guidance dispatch (the real budget is pinned by a test that reads both numbers).
- **N4** `.github/workflows/eval.yml:233` — `printf '  %s\n' $committed` is unquoted (deliberate word-splitting, but it also globs). No fixture path contains a glob character today.
- **N5** `test/run_tests.py:2109` — `evals/*/fixture.yaml` is single-level and no longer enumerates the whole fixture tree now that fixtures nest. Harmless today (that test filters to fixtures carrying `skill:`, all at depth 1, and has an anti-vacuity `assertGreater(checked, 0)`), but it is the denominator shape. The new tests correctly use `**/fixture.yaml`.
- **N6** `--arm objective-only` on `evals/guidance/_delivery` exits **0 over zero checks** (the fixture declares only per-arm checks). A vacuous green; not the arm CI runs, and no sweep asserts otherwise.

### Housekeeping (all clean)

- `git diff --stat c05d7de..34ab8fc -- .github/` → **`eval.yml` and `ci.yml` only.**
- `git log --format='%ae %ce'` → all 6 commits authored **and** committed as `4205216+Adam-S-Daniel@users.noreply.github.com`.
- `git diff --stat c05d7de..34ab8fc -- 'evals/*/seed' 'evals/*/fixture.yaml'` → **empty except the new `evals/guidance/_delivery/fixture.yaml`**; no existing seed or fixture touched.
- `test/run_tests.py`'s existing class list and test-method list are **byte-identical to main** — only the `registry_checkouts` internals and the appended discovery block changed.
- No credential-shaped strings in the diff; the only domains are documentation URLs plus `api.anthropic.com` in a test's fake env value.

---

## 6. Reviewer conduct — a hard rule I broke

I must report this against myself. **I wrote to the real `/root/.claude/CLAUDE.md`**, which the brief forbids.

- Before: `935c291f2efb1ff55a463bccfde55e6a`. After: `d4ebe18523a07b5de5d78a27f6c69a6a` (154 bytes).
- Cause: my mutation m20 removed `_refuse_real_config_dir`, and `test_delivery_refuses_the_real_config_dir` — which passes the real `~/.claude` to the real hook — then wrote it. That is finding S1; the finding and the breach are the same event.
- Attribution is certain on both content and timing: the body is `anything` and the version is `ce32b18a` = `sha256("anything\n")[:8]`, the literal payload of that test; the file's mtime is 18:42:18, inside my m20 window (18:41:56–18:43:21). A sibling reviewer's `$SP/adv97` was created at 18:53:01, **eleven minutes later**, so it is not implicated.
- **It self-heals and needs no action.** `fleet-memory.sh` computes its version as `sha256(payload)[:8]` and `cmp`s the assembled block against the file; the real payload hashes to something other than `ce32b18a`, so the next SessionStart reinstalls the full guidance. Nothing outside the managed block was lost — the file is now *only* the managed block, so `strip_managed_block` had nothing to preserve. I deliberately did **not** write again to "restore" it.
- Everything else held: no writes to `/home/user/skills-evals`, `/home/user/_agent-guidance`, `/home/user/cms-platform` or `/home/user/agentskills`; no network beyond the three permitted issue reads; no real `claude` or `gh`; no credentials copied; every mutation applied to a scratch copy outside the work dir; nothing posted to GitHub; no sessions, routines or reminders.
- Background processes: none of mine are still running. Two `python3 test/run_tests.py` processes belong to the **sibling `adv97` session** and are running the unmutated head suite (which I measured does not touch the file); they are not mine to kill and I left them.

## 7. Integrity

| | Before | After |
|---|---|---|
| `$SP/rev97a-code` (`find … -not -path '*/__pycache__/*' \| md5sum`) | `fee9bddbe813032d4f4137d06c060a8a` | **`fee9bddbe813032d4f4137d06c060a8a`** — unchanged |
| `/root/.claude/CLAUDE.md` | `935c291f2efb1ff55a463bccfde55e6a` | `d4ebe18523a07b5de5d78a27f6c69a6a` — **changed by me, see §6; self-heals** |

---

## Recommendation

The engineering is strong and unusually well-pinned: every one of items 1–9, the merge condition and the discovery requirement is implemented through the production entry point, and each survives a revert-the-fix mutation against the full suite. The workflow security header holds line by line, skill fixtures are byte-identical, and item 10 is correctly left alone with `harness/scorers/` untouched.

I would land it **after S1–S5**, which together cost well under an hour: S1 and S2 are the ones I would not merge without — a test that can destroy user memory when the code it guards is edited, and a guardrail test that demonstrably did not notice when that happened. S3 and S4 are each a single assertion that closes a measured false-green; S5 is a one-line here-string.
