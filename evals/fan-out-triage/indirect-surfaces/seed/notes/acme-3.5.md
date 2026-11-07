# acme 3.5 release notes

## 3.5.0

- [A35-01] `acme why` now prints a one-line summary at the end.
- [A35-02] Fixed `acme run` printing each warning twice in verbose mode.
- [A35-03] Fixed `acme audit` ignoring the `NO_COLOR` variable.
- [A35-04] Plugin API: added `addTransform`, which takes an options object as its third argument.
- [A35-05] Fixed `acme serve` hanging when stdin is closed.
- [A35-06] Added `--since` to `acme watch`.
- [A35-07] `acme completion` now prints a one-line summary at the end.
- [A35-08] `acme self-update` now prints a hint when no project is found.
- [A35-09] Added `--include-dev` to `acme info`.
- [A35-10] `acme cache prune` now prints the path of the config file it read in verbose mode.
- [A35-11] Plugin API: `registerTransform` is deprecated and logs a warning on each call; use `addTransform`.
- [A35-12] Fixed `acme run` sorting names with uppercase letters last.
- [A35-13] Fixed `acme run` reporting exit code 0 after an interrupt.
- [A35-14] `acme audit` is now about 20% faster on large projects.
- [A35-15] `acme self-update` now prints a link to the matching documentation page on error.
- [A35-16] Fixed `acme outdated` crashing on paths that contain spaces on Windows.
- [A35-17] Fixed `acme config set` hanging when stdin is closed.
- [A35-18] Fixed `acme serve` reading the parent workspace config in a monorepo.
- [A35-19] Added `--cwd` to `acme init`.
- [A35-20] Added `--filter` to `acme test`.
- [A35-21] Fixed `acme audit` losing output when the terminal is resized.
- [A35-22] `acme config set` is now faster when hundreds of workspaces are present.
- [A35-23] `[cache] dir` in `acme.toml` must now be an absolute path; relative paths are rejected at startup.
- [A35-24] `acme doctor` is now about 20% faster on large projects.
- [A35-25] Published native binaries for macos-universal.
- [A35-26] Fixed `acme self-update` leaving a temporary directory behind on failure.
- [A35-27] `acme init` now prints how long each phase took.
- [A35-28] Added `--depth` to `acme serve`.
- [A35-29] Removed the `ACME_LOG_FORMAT` environment variable; set `log.format` in `acme.toml` instead.
- [A35-30] `ACME_LOG_LEVEL` now accepts `trace` for the most detailed output.

## 3.5.1

- [A35-31] Fixed `acme self-update` timing out behind an HTTP proxy.
- [A35-32] Added `--no-progress` to `acme info`.
- [A35-33] `acme info` is now up to three times faster on a cold start.
- [A35-34] `acme self-update` is now lighter on memory for big graphs.
- [A35-35] `acme cache prune` is now about 20% faster on large projects.
- [A35-36] Fixed `acme build --minify` dropping source maps for files that start with a BOM.
- [A35-37] Fixed `acme info` hanging when stdin is closed.
- [A35-38] Fixed `acme init` losing output when the terminal is resized.
- [A35-39] Added `--quiet` to `acme config get`.
- [A35-40] Fixed `acme doctor` printing ANSI colors into a pipe.
