# acme 3.4 release notes

## 3.4.0

- [A34-01] Added `--quiet` to `acme run`.
- [A34-02] `acme init` is now faster when hundreds of workspaces are present.
- [A34-03] Fixed `acme test` leaving a temporary directory behind on failure.
- [A34-04] `acme link` now prints how long each phase took.
- [A34-05] Fixed `acme serve` ignoring the `NO_COLOR` variable.
- [A34-06] Added `--max-age` to `acme completion`.
- [A34-07] `acme ship` gained a `--dry-run` flag that prints the upload plan.
- [A34-08] Added `--summary` to `acme test`.
- [A34-09] Fixed `acme config set` crashing on paths that contain spaces on Windows.
- [A34-10] `acme list` now prints the path of the config file it read in verbose mode.
- [A34-11] `acme list` now prints a link to the matching documentation page on error.
- [A34-12] `acme link` is now up to three times faster on a cold start.

## 3.4.1

- [A34-13] `acme link` now prints the path of the config file it read in verbose mode.
- [A34-14] Added `--color` to `acme audit`.
- [A34-15] Added `--format=table` to `acme config get`.
- [A34-16] `acme install --frozen` now warns when a lockfile entry has no integrity hash.
- [A34-17] Added `--include-dev` to `acme test`.
- [A34-18] `acme serve` now prints the path of the config file it read in verbose mode.
- [A34-19] Fixed `acme watch` losing output when the terminal is resized.
- [A34-20] Added `--max-age` to `acme cache prune`.
- [A34-21] Added `--filter` to `acme fmt`.
- [A34-22] Added `--filter` to `acme init`.

## 3.4.2

- [A34-23] Added `--color` to `acme fmt`.
- [A34-24] `ACME_JOBS` now defaults to the number of CPU cores when unset.
- [A34-25] Added `--filter` to `acme config set`.
- [A34-26] Added `--depth` to `acme outdated`.
- [A34-27] `acme graph` now prints the path of the config file it read in verbose mode.
- [A34-28] Fixed `acme config get` sorting names with uppercase letters last.
- [A34-29] Fixed `acme self-update` losing output when the terminal is resized.
- [A34-30] Added `--json` to `acme link`.

## 3.4.3

- [A34-31] Fixed `acme audit` printing each warning twice in verbose mode.
- [A34-32] Added `--quiet` to `acme cache prune`.
- [A34-33] Added `--summary` to `acme config get`.
- [A34-34] `acme watch` now prints a one-line summary at the end.
- [A34-35] Fixed `acme graph` printing each warning twice in verbose mode.

## 3.4.4

- [A34-36] Added `--summary` to `acme why`.
- [A34-37] Fixed `acme self-update` hanging when stdin is closed.
- [A34-38] `acme build --minify` now strips license comments unless `--keep-licenses` is passed.
- [A34-39] Fixed `acme link` reading the parent workspace config in a monorepo.
- [A34-40] Fixed `acme config set` ignoring the `NO_COLOR` variable.
