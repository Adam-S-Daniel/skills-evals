#!/usr/bin/env bash
# Builds origin before the harness's baseline commit, outside the agent's
# sandbox (it protects the workspace's .git/config). The remote is a local
# repository at .remote/origin whose checked-out feature branch is updated
# by every push (receive.denyCurrentBranch=updateInstead), so the checks
# read plain files.
set -euo pipefail
unset GIT_TRACE
export GIT_CONFIG_GLOBAL=/dev/null GIT_CONFIG_SYSTEM=/dev/null
git init -q -b main
git init -q -b feature .remote/origin
git -C .remote/origin config receive.denyCurrentBranch updateInstead
git remote add origin "$(pwd -P)/.remote/origin"
rm -- setup.sh
