#!/usr/bin/env bash
# Build the handbook and publish it to gh-pages as one fresh commit.
set -euo pipefail

git config user.name "handbook-bot"
git config user.email "handbook-bot@example.com"

bash scripts/build-site.sh

source_rev=$(git rev-parse --short HEAD)
site=$(mktemp -d)
trap 'rm -rf "$site"' EXIT

cp -R public/. "$site/"
touch "$site/.nojekyll"

git -C "$site" init -q -b gh-pages
git -C "$site" add -A
git -C "$site" commit -q -m "handbook ${source_rev}"

git fetch -q "$site" gh-pages
git push -q --force origin FETCH_HEAD:refs/heads/gh-pages
echo "pages: published handbook ${source_rev}"
