# acme 2.x release notes (excerpt)

- [Q-01] Removed the `legacy_resolver` option from the `acme init` templates.
- [Q-02] Updated the colors of the bundled changelog viewer.
- [Q-03] Fixed a typo in the Portuguese help text.
- [Q-04] Improved startup time on Windows ARM.
- [Q-05] `acme.hooks.postBuild` now receives a build context object instead of the config.
- [Q-06] Added shell completions for fish.
- [Q-07] Fixed a crash when `acme doctor` runs without a TTY.
- [Q-08] `acme.hooks.preBuild` now receives a build context object instead of the config.
- [Q-09] Added a `--registry-timeout` flag to `acme publish`.
- [Q-10] Added a `--json` flag to `acme list`.
- [Q-11] `acme publish --registry` now rejects plain `http://` URLs.
- [Q-12] Removed the `legacy_resolver` option from `acme.toml`; the new resolver is always on.
