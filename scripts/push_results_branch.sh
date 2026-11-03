#!/usr/bin/env bash
# Push HEAD to <remote> <branch>, rebasing onto the remote tip when the push is
# rejected.
#
# Why: eval.yml's `publish` job and other workflows (the routine ingest,
# explorer-data, skill-coverage) all push persistent/eval-results, so a plain
# push can lose the race with
# "! [rejected] ... (fetch first)" and that eval's paid result is never
# published (run 41542886876). A fetch plus rebase is the wait between
# attempts, so there is no sleep.
#
# Usage: push_results_branch.sh <remote> <branch> [attempts, default 3]
#
# Auth is not this script's business: the caller supplies it through git
# config environment variables (GIT_CONFIG_COUNT and friends) for this one
# command, and this script never prints it.
set -euo pipefail

if [ "$#" -lt 2 ] || [ "$#" -gt 3 ]; then
  echo "usage: $0 <remote> <branch> [attempts]" >&2
  exit 2
fi
remote=$1
branch=$2
attempts=3
if [ "$#" -eq 3 ]; then attempts=$3; fi

case "$attempts" in
  ''|*[!0-9]*|0|0[0-9]*)
    echo "::error::attempts must be a positive integer"
    exit 2
    ;;
esac

attempt=1
while [ "$attempt" -le "$attempts" ]; do
  if git push "$remote" "HEAD:refs/heads/$branch"; then
    exit 0
  fi
  echo "Push attempt $attempt of $attempts was rejected." >&2
  if [ "$attempt" -eq "$attempts" ]; then
    break
  fi
  if ! git fetch "$remote" "$branch"; then
    echo "::error::could not fetch $remote $branch to retry the push"
    exit 1
  fi
  if ! git rebase "$remote/$branch"; then
    git rebase --abort || true
    echo "::error::rebasing onto $remote/$branch conflicted; the push was not retried"
    exit 1
  fi
  attempt=$((attempt + 1))
done
echo "::error::could not push to $remote $branch after $attempts attempts"
exit 1
