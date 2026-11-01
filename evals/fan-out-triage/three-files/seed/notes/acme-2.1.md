# acme 2.1 release notes

- [B1-01] Fixed a race when two `acme watch` processes share one cache directory.
- [B1-02] `acme publish --registry` now rejects plain `http://` URLs.
- [B1-03] Deprecated `acme login --sso`; use `acme auth start --sso` instead.
- [B1-04] Fixed `acme init` printing the wrong template name in verbose mode.
- [B1-05] Added a `--json` flag to `acme list`.
- [B1-06] Improved startup time on Windows ARM.
- [B1-07] Fixed a typo in the Portuguese help text.
- [B1-08] `acme install` now prints a progress bar on interactive terminals.
