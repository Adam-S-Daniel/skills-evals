#!/usr/bin/env bash
set -euo pipefail
export ACME_PROFILE=release
acme publish --registry http://registry.example.com/npm
