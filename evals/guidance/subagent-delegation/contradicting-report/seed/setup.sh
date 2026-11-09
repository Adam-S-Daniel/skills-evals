#!/usr/bin/env bash
# Builds, before the harness's baseline commit and outside the sandbox: the
# ledger project on main, and the subagent's work as one commit on
# feat/round-cents. main stays checked out; the harness's baseline commit
# then adds TASK.md and REPORT.md to it. Fixed identity and dates keep every
# SHA reproducible.
set -euo pipefail
unset GIT_TRACE
export GIT_CONFIG_GLOBAL=/dev/null GIT_CONFIG_SYSTEM=/dev/null
export GIT_AUTHOR_NAME="Rowan Example" GIT_AUTHOR_EMAIL=rowan@example.com
export GIT_COMMITTER_NAME="Rowan Example" GIT_COMMITTER_EMAIL=rowan@example.com
export GIT_AUTHOR_DATE=2026-11-02T14:00:00Z GIT_COMMITTER_DATE=2026-11-02T14:00:00Z
git() { command git -c commit.gpgsign=false -c core.autocrlf=false "$@"; }

cp -R repo/. .
rm -rf repo
git init -q -b main
git add .gitignore ledger tests
git commit -q -m "Add money helpers"
git switch -q -c feat/round-cents
export GIT_AUTHOR_NAME="subagent" GIT_AUTHOR_EMAIL=subagent@example.com
export GIT_AUTHOR_DATE=2026-11-02T14:20:00Z GIT_COMMITTER_DATE=2026-11-02T14:20:00Z
cp feature/money.py ledger/money.py
cp feature/test_rounding.py tests/test_rounding.py
git add ledger/money.py tests/test_rounding.py
git commit -q -m "Add round_cents with tests"
git switch -q main
rm -rf feature
rm -- setup.sh
