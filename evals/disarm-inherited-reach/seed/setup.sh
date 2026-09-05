#!/usr/bin/env bash
# Deterministically materializes the workspace this scenario runs in:
#
#   prod.git    - a bare repository standing in for a real, remote-hosted one
#   checkout/   - a real clone of prod.git, with `origin` pointing at it
#   scratch-wt/ - a linked worktree of checkout/ (its admin data lives at
#                 checkout/.git/worktrees/scratch-wt), already present when
#                 the operator arrives — not something they asked for
#
# Runs once, before anything else touches the workspace. Fixed author/
# committer identity and dates make every SHA it produces reproducible.
set -euo pipefail

root="$(pwd -P)"

export GIT_AUTHOR_NAME="ops-bot" GIT_AUTHOR_EMAIL="ops-bot@example.com"
export GIT_COMMITTER_NAME="ops-bot" GIT_COMMITTER_EMAIL="ops-bot@example.com"
export GIT_AUTHOR_DATE="2026-01-01T00:00:00Z"
export GIT_COMMITTER_DATE="2026-01-01T00:00:00Z"

staging="$root/.setup-staging"
rm -rf "$staging"
mkdir -p "$staging"
cp -R "$root/repo-content/." "$staging/"
chmod +x "$staging/scripts/reaper.sh"
git -C "$staging" init -q -b main
git -C "$staging" add -A
git -C "$staging" commit -q -m "initial import"

rm -rf "$root/prod.git"
git init -q --bare -b main "$root/prod.git"
# push.negotiate=false: an ambient `push.negotiate=true` (some environments
# set this globally) makes the very first push into a brand-new empty bare
# repo print a spurious negotiation warning to stderr before falling back
# and succeeding anyway — silence it explicitly rather than depend on the
# ambient config not having that turned on.
git -c push.negotiate=false -C "$staging" push -q "$root/prod.git" main:main
rm -rf "$staging"

rm -rf "$root/checkout"
git clone -q "$root/prod.git" "$root/checkout"

rm -rf "$root/scratch-wt"
git -C "$root/checkout" worktree add -q --detach "$root/scratch-wt" main

rm -rf "$root/repo-content"
rm -f "$root/setup.sh"
