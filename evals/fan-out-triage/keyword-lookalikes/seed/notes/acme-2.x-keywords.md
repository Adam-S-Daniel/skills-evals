# acme 2.x release notes (keyword-heavy)

- [K-01] `acme build` now reports the build target in its summary line.
- [K-02] Added a `--registry-timeout` flag to `acme publish`.
- [K-03] Added a `--json` flag to `acme list`.
- [K-04] Removed the `legacy_resolver` option from the `acme init` templates.
- [K-05] Fixed a race when two `acme watch` processes share one cache directory.
- [K-06] `acme.hooks.preBuild` now receives a build context object instead of the config.
- [K-07] Removed the `legacy_resolver` option from `acme.toml`; the new resolver is always on.
- [K-08] Deprecated `acme login --sso`; use `acme auth start --sso` instead.
- [K-09] Added `acme cache prune` to remove unused cache entries.
- [K-10] Deprecated `acme login --browser`; use `acme auth start` instead.
- [K-11] Fixed `acme init` printing the wrong template name in verbose mode.
- [K-12] `acme install` now prints a progress bar on interactive terminals.
- [K-13] Fixed a crash when `acme doctor` runs without a TTY.
- [K-14] `acme publish --registry` now rejects plain `http://` URLs.
- [K-15] `acme install --ci` now fails when the lockfile is out of date.
- [K-16] `acme.hooks.postBuild` now receives a build context object instead of the config.
