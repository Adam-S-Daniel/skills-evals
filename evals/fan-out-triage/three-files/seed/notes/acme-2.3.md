# acme 2.3 release notes

- [B3-01] Added Korean translations for error messages.
- [B3-02] Deprecated `acme login --browser`; use `acme auth start` instead.
- [B3-03] Removed the `legacy_resolver` option from `acme.toml`; the new resolver is always on.
- [B3-04] Added shell completions for fish.
- [B3-05] `acme install --ci` now fails when the lockfile is out of date.
- [B3-06] Fixed a typo in the French help text.
- [B3-07] Added `acme cache prune` to remove unused cache entries.
- [B3-08] Added a `--registry-timeout` flag to `acme publish`.
