#!/usr/bin/env bash
# Builds the release bundle. Keeps ExampleCLI's cache beside the build output.
set -euo pipefail
export EXAMPLE_CLI_CACHE_DIR="${PWD}/build/.cache"
example-cli bundle --out build/
