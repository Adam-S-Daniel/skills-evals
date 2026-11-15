# ExampleCLI release notes

## v5.0.0

[https://github.com/example-vendor/example-cli/releases/tag/v5.0.0](https://github.com/example-vendor/example-cli/releases/tag/v5.0.0)

### Breaking Changes

- Removed the `--legacy-output` flag from `example-cli check`; use `--format text` instead. (#2210) @mira-ortiz
- Renamed `EXAMPLE_CLI_CACHE_DIR` to `EXAMPLE_CLI_HOME`; the old name is now ignored. (#2231) @dev-lan

### Bug Fixes

- **windows:** handle UNC paths in `--config` (#2188)
- Fixed a crash on empty config files, a regression from 4.7.0 (#2150)

### Features

- Added a compact status line (#2203) @sam-okafor
- `example-cli doctor` now warns about unpinned plugins (#2240)
