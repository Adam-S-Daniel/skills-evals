## Verifiers

`export PATH=$SP/bin:$PATH` (mikefarah yq v4.53.3 first; `/usr/bin/yq` is a different tool),
`node_modules` copied from an existing checkout with a byte-identical `package-lock.json`
(no network, no `npm ci`).

| run | tree | environment | result | exit |
|---|---|---|---|---|
| 1 | `rev124a-code` (head `5215628`) | `env -u SP PATH=$SP/bin:$PATH` | **1359 passed, 0 failed** | 0 |
| 2 | `rev124a-ref` (`main` `3d972b4`) | same | **1256 passed, 0 failed** | 0 |
| 3 | `rev124a-code` | `env -i PATH=$SP/bin:/usr/bin:/bin:/usr/local/bin HOME=<scratch>` | **1359 passed, 0 failed** | 0 |

Both match the PR body exactly (it claims 1256 before, 1359 after). Head is green under a
constructed minimal environment too, so nothing in the new lane depends on ambient state.

**Assertion-set diff, not just counts.** Comparing the sorted PASS lines of run 1 against run 2:
105 lines present only at head, 2 present only at ref — and those 2 are the same two `big marker`
assertions with different numbers in their text (`74050-byte file` → `74816-byte file`), a benign
consequence of the guidance payload growing by the new section. **103 genuinely new assertions,
none removed** — exactly the 1359−1256 delta:

| area | new assertions |
|---|---|
| `instructions-loaded:` | 52 |
| `fleet-memory state:` | 21 |
| `instructions-report:` | 16 |
| `event seam:` | 7 |
| `self-hosted receipt:` | 3 |
| `repo-no-lock:` | 2 |
| `repo-ignored:` | 1 |
| `sync trigger: on.push.paths covers .claude/hooks/instructions-loaded.sh` | 1 |

**`test_fleet_memory_hook` is byte-for-byte unchanged.** Extracted from both trees
(233 lines each), `md5 = 92a1d08023562e441bf5ee4cdc005ef4` on both, `diff` empty. The PR body's
claim holds.

**Hollowness.** Head's `test/run-tests.sh` dropped onto the ref tree: the suite aborts under
`set -e` partway through `test_instructions_loaded_hook` (a `wc -l <` on a log the missing hook
never wrote), having already logged 29 FAILs. Re-run through a driver that sources the same
prelude with `set +e` and calls only the five new test functions:

| tree | result |
|---|---|
| head | 99 passed, 0 failed |
| ref + head's tests | **18 passed, 59 failed** |

The 18 that pass on ref are all vacuous-by-construction negatives against a file that does not
exist there (`assert_not_contains "$INSTR_HOOK" '"decision"'`, "nothing outside the config dir was
written", "no interpreter traceback", "an unset HOME is not a shell error", "earlier sessions are
not in the default report"). Every positive assertion in the five blocks is red on the base.
