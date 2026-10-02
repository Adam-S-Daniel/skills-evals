#!/usr/bin/env bash
# Publish the model-usage census to the `persistent/eval-results` branch.
#
# Runs on the OWNER'S DURABLE MACHINE, never in CI or a cloud session: the
# census reads local Claude Code transcripts (~/.claude/projects), which
# those surfaces do not have. See evals/usage/CENSUS.md for what it is, the
# privacy contract on its output, and how to schedule this script.
#
# Steps, all inside one temp dir that is removed on exit:
#   1. shallow-clone skills-evals and run ITS copy of
#      scripts/model_usage_census.py against the real transcripts;
#   2. shallow-clone the persistent/eval-results branch, copy in usage/latest.json;
#   3. commit "propagation: usage census [skip ci]" ONLY if the census
#      changed, and push it (one `pull --rebase` retry when the push is not a
#      fast-forward);
#   4. verify with `git merge-base --is-ancestor HEAD origin/persistent/eval-results` —
#      a push that printed success is not proof the commit is on the branch.
#
# Credentials: whatever git already has on this machine. This script handles
# no token and reads no secret.
#
# Usage: scripts/publish_usage_census.sh [--dry-run]
#   --dry-run   do everything except push
#
# Output: one summary line — totals only, no model ids, no paths.
#
# Test seams (all optional; the defaults are the real thing):
#   SKILLS_EVALS_URL  where to clone from (default: the GitHub repo)
#   CENSUS_PROJECTS   transcript root (default: the census's own ~/.claude/projects)
#   CENSUS_NOW        ISO-8601 instant handed to the census as `--now`
#   PYTHON            interpreter (default python3)
set -euo pipefail

URL="${SKILLS_EVALS_URL:-https://github.com/Adam-S-Daniel/skills-evals.git}"
BRANCH="persistent/eval-results"
PY="${PYTHON:-python3}"
# A census whose counts did not change is still re-published once its
# generated_at is this old: harness/roster.py treats a census older than 14
# days as "no fresh census", so an idle account must not age out of it.
REFRESH_DAYS=6
dry_run=0

case "${1:-}" in
  "") ;;
  --dry-run) dry_run=1 ;;
  *) echo "usage: $0 [--dry-run]" >&2; exit 2 ;;
esac
[ "$#" -le 1 ] || { echo "usage: $0 [--dry-run]" >&2; exit 2; }

tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT

# The machine's git identity when it has one; a noreply fallback when it does
# not, so a fresh box can still commit.
ident=()
if [ -z "$(git config user.email 2>/dev/null || true)" ]; then
  ident=(-c user.name=usage-census -c user.email=usage-census@users.noreply.github.com)
fi

git clone --quiet --depth 1 "$URL" "$tmp/src" >/dev/null 2>&1 \
  || { echo "usage census: could not clone skills-evals" >&2; exit 1; }

census_args=(--out "$tmp/usage/latest.json")
if [ -n "${CENSUS_PROJECTS:-}" ]; then census_args+=(--projects "$CENSUS_PROJECTS"); fi
if [ -n "${CENSUS_NOW:-}" ]; then census_args+=(--now "$CENSUS_NOW"); fi
# The census's own status line names its output path; this script prints its
# own summary instead. stderr stays: its messages name no path.
"$PY" "$tmp/src/scripts/model_usage_census.py" "${census_args[@]}" >/dev/null

git clone --quiet --depth 1 --single-branch --branch "$BRANCH" "$URL" "$tmp/results" >/dev/null 2>&1 \
  || { echo "usage census: could not clone the $BRANCH branch" >&2; exit 1; }

# Totals for the summary line, and the changed/unchanged decision. Both read
# only the two JSON files; neither uses the clock.
decision="$("$PY" - "$tmp/usage/latest.json" "$tmp/results/usage/latest.json" "$REFRESH_DAYS" <<'PY'
import json, sys
from datetime import datetime

new_path, old_path, refresh_days = sys.argv[1], sys.argv[2], int(sys.argv[3])
new = json.load(open(new_path, encoding="utf-8"))
turns = sum(sum(w.values()) for w in new["counts"].values())
models = len(new["counts"])
state = "changed"
try:
    old = json.load(open(old_path, encoding="utf-8"))
    stamp = "%Y-%m-%dT%H:%M:%SZ"
    age = (datetime.strptime(new["generated_at"], stamp)
           - datetime.strptime(old["generated_at"], stamp))
    if (old.get("counts") == new["counts"] and old.get("weeks") == new["weeks"]
            and 0 <= age.total_seconds() < refresh_days * 86400):
        state = "unchanged"
except (OSError, ValueError, KeyError, TypeError, AttributeError):
    pass
print(f"{state} {models} {turns} {len(new['weeks'])}")
PY
)"
read -r state models turns weeks <<<"$decision"

summary="usage census: $models models, $turns assistant turns, $weeks weeks"

if [ "$state" = "unchanged" ]; then
  echo "$summary; unchanged, nothing published"
  exit 0
fi

mkdir -p "$tmp/results/usage"
cp "$tmp/usage/latest.json" "$tmp/results/usage/latest.json"
git -C "$tmp/results" add usage/latest.json
staged="$(git -C "$tmp/results" diff --cached --name-only)"
if [ "$staged" != "usage/latest.json" ]; then
  echo "usage census: unexpected staged paths; refusing to commit" >&2
  exit 1
fi
git -C "$tmp/results" "${ident[@]+"${ident[@]}"}" commit --quiet \
  -m "propagation: usage census [skip ci]" >/dev/null

if [ "$dry_run" = 1 ]; then
  echo "$summary; dry run, committed locally and pushed nothing"
  exit 0
fi

if ! git -C "$tmp/results" push --quiet origin "HEAD:$BRANCH" >/dev/null 2>&1; then
  # Non-fast-forward: someone published since the clone. Rebase once, retry once.
  git -C "$tmp/results" "${ident[@]+"${ident[@]}"}" pull --rebase --quiet origin "$BRANCH" >/dev/null 2>&1 \
    || { echo "usage census: rebase onto $BRANCH failed" >&2; exit 1; }
  git -C "$tmp/results" push --quiet origin "HEAD:$BRANCH" >/dev/null 2>&1 \
    || { echo "usage census: push to $BRANCH failed" >&2; exit 1; }
fi

# A successful push is not proof the commit exists on the branch.
git -C "$tmp/results" fetch --quiet origin "$BRANCH" >/dev/null 2>&1
if ! git -C "$tmp/results" merge-base --is-ancestor HEAD "origin/$BRANCH"; then
  echo "usage census: pushed, but the commit is not on origin/$BRANCH" >&2
  exit 1
fi
echo "$summary; published"
