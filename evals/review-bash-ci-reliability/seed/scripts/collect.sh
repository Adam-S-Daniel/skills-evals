#!/usr/bin/env bash
# Collect the packages changed since the last release, via the GitHub API.
# Placeholder for the real collection call; the eval never executes this script.
set -euo pipefail

REPO="example-org/example-repo"

out=$(gh api "repos/${REPO}/pulls?state=merged" --jq '.[].title') || true

if [[ -z "$out" ]]; then
    echo "No merged PRs found; nothing to release."
    exit 0
fi

echo "$out" > changed-packages.txt

tmp_response="/tmp/collect-response.$$"
rm -f "$tmp_response" || true  # temp file cleanup; harmless if it's already gone
