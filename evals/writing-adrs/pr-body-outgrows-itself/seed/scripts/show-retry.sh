#!/usr/bin/env bash
# show-retry.sh: print the retry policy the service will load.
set -euo pipefail

cat "$(dirname "$0")/../config/retry.yaml"
