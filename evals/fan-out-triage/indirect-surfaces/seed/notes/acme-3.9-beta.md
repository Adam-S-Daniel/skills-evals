# acme 3.9-beta release notes

Pre-release. Not for production use; stable users stay on 3.8.

## 3.9.0-beta.1

- [A39-01] Fixed `acme why` timing out behind an HTTP proxy.
- [A39-02] Fixed `acme test` crashing on paths that contain spaces on Windows.
- [A39-03] Added `--json` to `acme doctor`.
- [A39-04] Fixed `acme test` timing out behind an HTTP proxy.
- [A39-05] Fixed `acme run` leaving a temporary directory behind on failure.
- [A39-06] Added `--since` to `acme exec`.
- [A39-07] Added `--summary` to `acme info`.
- [A39-08] `acme ship` no longer accepts `--channel`; set `[ship] channel` in `acme.toml` instead.
- [A39-09] Fixed `acme config get` losing output when the terminal is resized.
- [A39-10] Added `--max-age` to `acme audit`.
- [A39-11] `acme config get` now prints a link to the matching documentation page on error.
- [A39-12] Fixed `acme info` reporting exit code 0 after an interrupt.
- [A39-13] `acme outdated` is now lighter on memory for big graphs.
- [A39-14] `acme fmt` now prints the path of the config file it read in verbose mode.
- [A39-15] Plugin API: removed `onAsset`; use `onEmit`, which receives the same asset object.
- [A39-16] Added `--format=table` to `acme test`.
- [A39-17] Added `--color` to `acme graph`.
- [A39-18] Fixed `acme exec` leaving a temporary directory behind on failure.
- [A39-19] Fixed `acme graph` losing output when the terminal is resized.
- [A39-20] Published native binaries for windows-arm64.
- [A39-21] Fixed `acme link` reporting exit code 0 after an interrupt.
- [A39-22] Added `--color` to `acme why`.
- [A39-23] Fixed `acme exec` timing out behind an HTTP proxy.
- [A39-24] Fixed `acme doctor` reporting exit code 0 after an interrupt.
- [A39-25] Fixed `acme why` reading the parent workspace config in a monorepo.
- [A39-26] Fixed `acme cache prune` reading the parent workspace config in a monorepo.
- [A39-27] `acme install --frozen` is removed; use `acme install --locked` instead.
- [A39-28] Added `--json` to `acme config set`.
- [A39-29] Added `--since` to `acme cache prune`.
- [A39-30] Fixed `acme list` sorting names with uppercase letters last.
- [A39-31] `acme config set` is now lighter on memory for big graphs.
- [A39-32] Fixed `acme audit` rejecting a project path that is a symlink.
- [A39-33] Fixed `acme serve` timing out behind an HTTP proxy.
- [A39-34] Fixed `acme graph` reporting exit code 0 after an interrupt.
- [A39-35] `acme init` now prints a hint when no project is found.
- [A39-36] Added `--quiet` to `acme config set`.
- [A39-37] Added `--format=table` to `acme outdated`.
- [A39-38] `acme test` is now about 20% faster on large projects.
- [A39-39] Documented the plugin authoring guide.
- [A39-40] `acme init` is now up to three times faster on a cold start.
