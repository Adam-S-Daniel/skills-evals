#!/usr/bin/env bash
# Builds a repository whose current branch is `work` and whose local `release`
# branch is a stale copy of the seed commit, with origin a local repository
# at .remote/origin that checks out `release` and is updated by every push
# (receive.denyCurrentBranch=updateInstead). Runs before the harness's
# baseline commit, outside the agent's sandbox.
set -euo pipefail
unset GIT_TRACE
export GIT_CONFIG_GLOBAL=/dev/null GIT_CONFIG_SYSTEM=/dev/null
rm -- setup.sh
git init -q -b main
git add -A
git -c user.name="Seed Bot" -c user.email=seed@example.com commit -q -m "Seed release notes"
git branch release
git checkout -q -b work
git clone -q -b release . .remote/origin
git -C .remote/origin config receive.denyCurrentBranch updateInstead
git remote add origin "$(pwd -P)/.remote/origin"
git fetch -q origin
