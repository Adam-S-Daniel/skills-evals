#!/usr/bin/env bash
# Install what .github/workflows/ci.yml's `test` job installs, so a fresh
# machine or cloud session can run this repo's tests. ci.yml is the source of
# truth: test/issues/test_issue_dev_setup.py fails when the two lists drift.
# The script never uses sudo and does not install bubblewrap (bwrap).
#
#   bash scripts/dev_setup.sh                  install everything
#   bash scripts/dev_setup.sh --print-pins     list the pip pins, install nothing
#   bash scripts/dev_setup.sh --print-npm-dirs list the npm dirs, install nothing
set -euo pipefail

PIP_PINS=(
  pyyaml==6.0.3
  markdown-it-py==4.2.0
  tree-sitter==0.26.0
  tree-sitter-bash==0.25.1
  pytest==9.1.1
  pytest-xdist==3.8.0
)

NPM_DIRS=(
  evals/browser-testing/seed
  evals/real-work/_agent-guidance-196/seed
  evals/real-work/cms-platform-221/seed/e2e
  evals/real-work/cms-platform-693/seed/e2e
)

if [ "$#" -gt 1 ]; then
  echo "usage: dev_setup.sh [--print-pins | --print-npm-dirs]" >&2
  exit 2
fi
if [ "$#" -eq 1 ]; then
  case "$1" in
    --print-pins) printf '%s\n' "${PIP_PINS[@]}"; exit 0 ;;
    --print-npm-dirs) printf '%s\n' "${NPM_DIRS[@]}"; exit 0 ;;
    *) echo "usage: dev_setup.sh [--print-pins | --print-npm-dirs]" >&2; exit 2 ;;
  esac
fi

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# A PEP 668 "externally managed" Python refuses the first form.
if ! python3 -m pip install "${PIP_PINS[@]}"; then
  python3 -m pip install --break-system-packages "${PIP_PINS[@]}"
fi

for dir in "${NPM_DIRS[@]}"; do
  (cd "$REPO_ROOT/$dir" && npm ci --ignore-scripts --no-audit --no-fund)
done

if ! command -v bwrap >/dev/null 2>&1; then
  echo "dev_setup: bubblewrap (bwrap) not found; tests of workspace-executing scorers fail closed without it. CI installs it; see .github/workflows/ci.yml." >&2
fi

echo "dev_setup: done."
echo "Run one module:  python3 -m pytest test/issues/<file>.py -q -n 2      Full suite:  python3 test/run_tests.py --jobs auto"
