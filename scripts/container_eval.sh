#!/usr/bin/env bash
# Host-side wrapper: run scripts/local_eval.py inside a Docker container,
# authenticating with a long-lived OAuth token (`claude setup-token`) that
# reaches the container only through `docker run --env-file`.
#
# Usage:
#   scripts/container_eval.sh --token-file PATH --image IMAGE \
#       --results-dir DIR -- <local_eval args...>
#
# The token file holds one `CLAUDE_CODE_OAUTH_TOKEN=...` line, mode 600 or 400,
# outside any git work tree. Its contents are never printed or passed on a
# command line. The exit code is docker's.
set -euo pipefail

die() { echo "container_eval: $*" >&2; exit 2; }

usage() {
  echo "usage: $0 --token-file PATH --image IMAGE --results-dir DIR -- <local_eval args...>" >&2
  exit 2
}

token_file="" image="" results_dir=""
while [ "$#" -gt 0 ]; do
  case "$1" in
    --token-file) [ "$#" -ge 2 ] || usage; token_file=$2; shift 2 ;;
    --image) [ "$#" -ge 2 ] || usage; image=$2; shift 2 ;;
    --results-dir) [ "$#" -ge 2 ] || usage; results_dir=$2; shift 2 ;;
    --) shift; break ;;
    *) usage ;;
  esac
done
[ -n "$token_file" ] && [ -n "$image" ] && [ -n "$results_dir" ] || usage

[ -e "$token_file" ] || die "token file does not exist: $token_file"
[ -f "$token_file" ] && [ ! -L "$token_file" ] || die "token file is not a regular file: $token_file"
mode=$(stat -c '%a' -- "$token_file")
case "$mode" in
  600|400) ;;
  *) die "token file mode is $mode; it must be 600 or 400 (no group or other access)" ;;
esac
token_dir=$(cd -- "$(dirname -- "$token_file")" && pwd -P)
if git -C "$token_dir" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  die "token file is inside a git work tree; keep it outside every repository"
fi

if [ -e "$results_dir" ]; then
  [ -d "$results_dir" ] || die "results dir is not a directory: $results_dir"
  if [ -n "$(ls -A -- "$results_dir")" ]; then
    die "results dir is not empty: $results_dir"
  fi
fi
mkdir -p -- "$results_dir"
results_dir=$(cd -- "$results_dir" && pwd -P)

repo_root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)

cmd=(docker run --rm
  --env-file "$token_file"
  -e SKILLS_EVALS_IN_CONTAINER=1
  -u "$(id -u):$(id -g)"
  -v "$repo_root:/src:ro"
  -v "$results_dir:/results"
  -w /work
  "$image"
  bash -c 'cp -a /src /work/skills-evals && cd /work/skills-evals && exec python3 scripts/local_eval.py "$@" --container-token --results-dir /results'
  _ "$@")

exec "${cmd[@]}"
