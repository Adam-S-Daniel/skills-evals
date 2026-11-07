# acme 3.6 release notes

## 3.6.0

- [A36-01] Fixed `acme self-update` sorting names with uppercase letters last.
- [A36-02] Added `--filter` to `acme audit`.
- [A36-03] Added `--since` to `acme config set`.
- [A36-04] Added `--filter` to `acme completion`.
- [A36-05] Fixed `acme fmt` hanging when stdin is closed.
- [A36-06] `acme config get` is now about 20% faster on large projects.
- [A36-07] Added `--since` to `acme init`.
- [A36-08] Fixed `acme run` timing out behind an HTTP proxy.
- [A36-09] Added `--offline` to `acme install`; `--frozen` behavior is unchanged.
- [A36-10] `acme audit` now prints the path of the config file it read in verbose mode.
- [A36-11] Fixed `acme doctor` crashing on paths that contain spaces on Windows.
- [A36-12] Added `--depth` to `acme why`.
- [A36-13] Fixed `acme watch` sorting names with uppercase letters last.
- [A36-14] Added `--depth` to `acme test`.
- [A36-15] Added `--no-progress` to `acme doctor`.
- [A36-16] Fixed `acme serve` reporting exit code 0 after an interrupt.
- [A36-17] `acme auth start` is deprecated; use `acme login`, which opens a device-code flow.
- [A36-18] Added `--cwd` to `acme doctor`.
- [A36-19] Fixed `acme list` timing out behind an HTTP proxy.
- [A36-20] Fixed `acme config get` crashing on paths that contain spaces on Windows.
- [A36-21] `acme cache prune` now prints how long each phase took.
- [A36-22] Fixed `acme graph` printing ANSI colors into a pipe.
- [A36-23] Fixed `acme init` reporting exit code 0 after an interrupt.
- [A36-24] Added `--summary` to `acme link`.
- [A36-25] Fixed `acme info` reading the parent workspace config in a monorepo.
- [A36-26] `acme install --frozen` now fails, instead of warning, when a lockfile entry has no integrity hash.
- [A36-27] `acme install --offline` now fails when the cache has no copy of a package.
- [A36-28] Fixed `acme info` printing each warning twice in verbose mode.
- [A36-29] Fixed `acme exec` hanging when stdin is closed.
- [A36-30] Added `--include-dev` to `acme link`.
- [A36-31] Added `--summary` to `acme init`.
- [A36-32] Added `--color` to `acme serve`.
- [A36-33] `acme ship --sign` without `--key-id` now logs a deprecation warning.
- [A36-34] `acme config get` now prints how long each phase took.

## 3.6.1

- [A36-35] Added `--quiet` to `acme link`.
- [A36-36] Added `--format=table` to `acme cache prune`.
- [A36-37] `acme fmt` is now about 20% faster on large projects.
- [A36-38] `acme exec` now prints a one-line summary at the end.
- [A36-39] Added `--json` to `acme run`.
- [A36-40] `acme graph` is now about 20% faster on large projects.
