#!/usr/bin/env bash
# Rebuild the nightly snapshot and commit it to main when it changed.
set -euo pipefail

version=$(dasel -f manifest.toml '.package.version' 2>/dev/null || echo unknown)

bash scripts/build-snapshot.sh

git config user.name "snapshot-bot"
git config user.email "snapshot-bot@example.com"

changed=$(git status --porcelain -- snapshot/ | grep -c .)
if [[ "$changed" -eq 0 ]]; then
    echo "snapshot: no changes"
    exit 0
fi

git add snapshot/
git commit -q -m "snapshot ${version}"
git push -q origin HEAD
echo "snapshot: committed ${version} (${changed} file(s))"
