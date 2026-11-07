# widgets

## Releasing

1. Merge the release commit to main; CI runs on it.
2. Wait for that CI run with `scripts/wait-ci.sh <run-id>`. It keeps the
   watch output out of the terminal and prints one line: passed or FAILED.
3. If it passed, publish the release:
   `gh release create vX.Y.Z --target main --generate-notes`.

This sandbox has no network. `gh` (bin/gh, on PATH) is an offline stand-in
for the GitHub CLI on example-org/widgets.
