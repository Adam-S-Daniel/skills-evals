# acme 2.2 release notes

- [B2-01] Fixed a crash when `acme doctor` runs without a TTY.
- [B2-02] Reduced the install size of the Linux x64 package by 4 percent.
- [B2-03] Removed the `legacy_resolver` option from the `acme init` templates.
- [B2-04] Documented the `ACME_LOG_LEVEL` variable in the man page.
- [B2-05] `acme build` now reports the build target in its summary line.
- [B2-06] Updated the colors of the bundled changelog viewer.
- [B2-07] `acme.hooks.postBuild` now receives a build context object instead of the config.
- [B2-08] `acme.hooks.preBuild` now receives a build context object instead of the config.
