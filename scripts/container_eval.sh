#!/usr/bin/env bash
# Host-side wrapper: run scripts/local_eval.py inside a sealed Docker
# container, authenticating with a long-lived OAuth token (`claude
# setup-token`). Each run gets its own internal network, one sidecar on it
# and a runner; all three are removed when the script ends.
#
# Usage:
#   scripts/container_eval.sh --token-file PATH --image IMAGE \
#       --results-dir DIR [--mode credproxy|allowlist] \
#       [--credproxy-image IMG] [--egress-image IMG] [--seccomp PROFILE] \
#       [--context-repo PATH]... -- <local_eval args...>
#
# The token file holds exactly one `CLAUDE_CODE_OAUTH_TOKEN=<token>` line
# ([A-Za-z0-9_-] only), mode 600 or 400, outside any git work tree. Its
# contents are never printed or passed on a command line. The exit code is the
# runner's.
#
# The network is `docker network create --internal` with the isolated IPv4
# gateway mode: nothing on it reaches the host or the internet. The sidecar
# is started on the default bridge, then connected to that network, so it is
# the one way out. The runner is on the internal network only.
#
#   --mode credproxy (default): the sidecar (--credproxy-image, nginx) holds
#     the token and adds the Authorization header; it forwards only the
#     Anthropic API. The runner can reach that sidecar and nothing else. It
#     holds a dummy token and ANTHROPIC_BASE_URL=http://<sidecar>:8080, never
#     the real token: the token file is mounted read-only into the sidecar
#     alone. A prompt-injected arm has no credential to read or to send out.
#   --mode allowlist: the sidecar (--egress-image, squid) allows only the
#     hosts its allowlist names and holds no credential. The runner gets the
#     token file through --env-file and reaches the network only through
#     that proxy (HTTPS_PROXY/HTTP_PROXY). The token is in the runner.
#
# The runner is sealed: the host user's uid:gid, every capability dropped,
# no-new-privileges, a read-only root, tmpfs for /tmp, /home/eval and /work,
# and --seccomp (default docker/eval-runner/seccomp-bwrap.json), Docker's
# default profile plus the namespace syscalls bubblewrap needs. This
# checkout is mounted read-only at /src and copied to /work/skills-evals.
# Each --context-repo PATH (a registry or other checkout the fixtures name) is
# mounted read-only at /work/<its directory name>, a sibling of that copy. A
# linked git worktree (its `.git` is a file) also gets its common git dir
# mounted read-only at the same absolute path, or git cannot read its SHA.
# Binds use --mount, so a `:` in a path means nothing; a `,` would, so a path
# holding one is refused.
set -euo pipefail

die() { echo "container_eval: $*" >&2; exit 2; }

usage() {
  echo "usage: $0 --token-file PATH --image IMAGE --results-dir DIR" \
    "[--mode credproxy|allowlist] [--credproxy-image IMG] [--egress-image IMG]" \
    "[--seccomp PROFILE] [--context-repo PATH]... -- <local_eval args...>" >&2
  exit 2
}

token_file="" image="" results_dir="" seccomp=""
mode=credproxy credproxy_image=skills-evals-credproxy egress_image=skills-evals-egress
context_args=()
while [ "$#" -gt 0 ]; do
  case "$1" in
    --token-file) [ "$#" -ge 2 ] || usage; token_file=$2; shift 2 ;;
    --image) [ "$#" -ge 2 ] || usage; image=$2; shift 2 ;;
    --results-dir) [ "$#" -ge 2 ] || usage; results_dir=$2; shift 2 ;;
    --mode) [ "$#" -ge 2 ] || usage; mode=$2; shift 2 ;;
    --credproxy-image) [ "$#" -ge 2 ] || usage; credproxy_image=$2; shift 2 ;;
    --egress-image) [ "$#" -ge 2 ] || usage; egress_image=$2; shift 2 ;;
    --seccomp) [ "$#" -ge 2 ] || usage; seccomp=$2; shift 2 ;;
    --context-repo) [ "$#" -ge 2 ] || usage; context_args+=("$2"); shift 2 ;;
    --) shift; break ;;
    *) usage ;;
  esac
done
[ -n "$token_file" ] && [ -n "$image" ] && [ -n "$results_dir" ] || usage
case "$mode" in
  credproxy|allowlist) ;;
  *) die "unknown --mode: $mode (use credproxy or allowlist)" ;;
esac

repo_root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)

# A comma would end a --mount field early and let the rest of the path set
# mount options.
no_comma() {
  case "$1" in
    *,*) die "$2 contains a comma, which docker's --mount syntax cannot carry: $1" ;;
  esac
}

[ -e "$token_file" ] || die "token file does not exist: $token_file"
[ -f "$token_file" ] && [ ! -L "$token_file" ] || die "token file is not a regular file: $token_file"
mode_bits=$(stat -c '%a' -- "$token_file")
case "$mode_bits" in
  600|400) ;;
  *) die "token file mode is $mode_bits; it must be 600 or 400 (no group or other access)" ;;
esac
token_dir=$(cd -- "$(dirname -- "$token_file")" && pwd -P)
if git -C "$token_dir" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  die "token file is inside a git work tree; keep it outside every repository"
fi
# Shape only, and without printing a byte of it: one line, the variable name,
# then token characters. grep -q prints nothing; its exit code is the answer.
token_lines=$(LC_ALL=C grep -c '' -- "$token_file" || true)
if [ "$token_lines" != 1 ] \
    || ! LC_ALL=C grep -qxE 'CLAUDE_CODE_OAUTH_TOKEN=[A-Za-z0-9_-]+' -- "$token_file"; then
  die "token file must be exactly one line, CLAUDE_CODE_OAUTH_TOKEN= followed by [A-Za-z0-9_-] characters"
fi
token_file=$(cd -- "$token_dir" && pwd -P)/$(basename -- "$token_file")
no_comma "$token_file" "token file path"

if [ -z "$seccomp" ]; then
  seccomp=$repo_root/docker/eval-runner/seccomp-bwrap.json
fi
[ -f "$seccomp" ] || die "seccomp profile is not a regular file: $seccomp"
seccomp=$(cd -- "$(dirname -- "$seccomp")" && pwd -P)/$(basename -- "$seccomp")

# Context repos: real directories, each mounted beside the harness copy.
context_mounts=() context_dirs=() context_names=()
for given in ${context_args[@]+"${context_args[@]}"}; do
  [ -d "$given" ] || die "--context-repo is not an existing directory: $given"
  dir=$(cd -- "$given" && pwd -P)
  no_comma "$dir" "--context-repo path"
  name=$(basename -- "$dir")
  [ "$name" != skills-evals ] || die "--context-repo may not be named skills-evals (that is the harness copy): $given"
  for seen in ${context_names[@]+"${context_names[@]}"}; do
    [ "$seen" != "$name" ] || die "two --context-repo directories are named $name; each mounts at /work/<name>"
  done
  context_names+=("$name")
  context_dirs+=("$dir")
  context_mounts+=(--mount "type=bind,src=$dir,dst=/work/$name,readonly")
done

# A linked worktree's `.git` is a file pointing into the main repository's git
# dir; mount that dir (read-only) at the same path so git resolves it.
git_mounts=() mounted_common=()
for dir in "$repo_root" ${context_dirs[@]+"${context_dirs[@]}"}; do
  [ -f "$dir/.git" ] || continue
  common=$(git -C "$dir" rev-parse --path-format=absolute --git-common-dir 2>/dev/null) \
    || die "cannot find the git common dir of the linked worktree $dir"
  no_comma "$common" "git common dir"
  duplicate=""
  for seen in ${mounted_common[@]+"${mounted_common[@]}"}; do
    [ "$seen" != "$common" ] || duplicate=1
  done
  [ -z "$duplicate" ] || continue
  mounted_common+=("$common")
  git_mounts+=(--mount "type=bind,src=$common,dst=$common,readonly")
done

if [ -e "$results_dir" ]; then
  [ -d "$results_dir" ] || die "results dir is not a directory: $results_dir"
  if [ -n "$(ls -A -- "$results_dir")" ]; then
    die "results dir is not empty: $results_dir"
  fi
fi
mkdir -p -- "$results_dir"
results_dir=$(cd -- "$results_dir" && pwd -P)
no_comma "$results_dir" "results dir path"
no_comma "$repo_root" "checkout path"

uid=$(id -u) gid=$(id -g)
net="skills-evals-$$-$(od -An -N4 -tx1 /dev/urandom | tr -d ' \n')"
runner="$net-runner"
scratch=""
if [ "$mode" = credproxy ]; then sidecar="$net-credproxy"; else sidecar="$net-egress"; fi

# Runs on every exit (also INT and TERM, turned into exits below): remove the
# runner, the sidecar and the network, and the dummy token's directory.
# Output is discarded and a failure is ignored, so the script's exit code stays
# the runner's.
# shellcheck disable=SC2317  # run through the trap below
cleanup() {
  docker rm -f "$runner" >/dev/null 2>&1 || true
  docker rm -f "$sidecar" >/dev/null 2>&1 || true
  docker network rm "$net" >/dev/null 2>&1 || true
  if [ -n "$scratch" ]; then rm -rf -- "$scratch" || true; fi
}
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

docker network create --internal \
  -o com.docker.network.bridge.gateway_mode_ipv4=isolated "$net" >/dev/null

sidecar_failed() {
  docker logs "$sidecar" >&2 || true
  die "$1"
}

if [ "$mode" = credproxy ]; then
  docker run -d --name "$sidecar" --network bridge \
    -u "$uid:$gid" --read-only \
    --tmpfs "/tmp:rw,size=64m,uid=$uid,gid=$gid,mode=0700" \
    --cap-drop ALL --security-opt no-new-privileges \
    --mount "type=bind,src=$token_file,dst=/run/secrets/oauth.env,readonly" \
    "$credproxy_image" >/dev/null
  # The runner gets a placeholder that the proxy replaces; the real token
  # stays in the sidecar.
  scratch=$(mktemp -d)
  dummy_env=$scratch/dummy.env
  (umask 077 && printf 'CLAUDE_CODE_OAUTH_TOKEN=dummy-not-a-token\n' > "$dummy_env")
  chmod 600 -- "$dummy_env"
  mode_args=(--env-file "$dummy_env" -e "ANTHROPIC_BASE_URL=http://$sidecar:8080")
else
  docker run -d --name "$sidecar" --network bridge \
    --read-only --cap-drop ALL --security-opt no-new-privileges \
    "$egress_image" >/dev/null
  mode_args=(--env-file "$token_file"
    -e "HTTPS_PROXY=http://$sidecar:3128" -e "HTTP_PROXY=http://$sidecar:3128")
fi
docker network connect "$net" "$sidecar" \
  || sidecar_failed "could not connect the $sidecar sidecar to $net"
running=$(docker inspect -f '{{.State.Running}}' "$sidecar" 2>/dev/null || true)
[ "$running" = true ] || sidecar_failed "the $sidecar sidecar is not running"

runner_cmd=(docker run --rm --name "$runner" --network "$net"
  -u "$uid:$gid"
  --cap-drop ALL
  --security-opt "seccomp=$seccomp"
  --security-opt no-new-privileges
  --read-only
  --tmpfs "/tmp:rw,exec,nosuid,nodev,size=1g"
  --tmpfs "/home/eval:rw,exec,nosuid,nodev,size=512m,uid=$uid,gid=$gid,mode=0700"
  --tmpfs "/work:rw,exec,nosuid,nodev,size=4g,uid=$uid,gid=$gid"
  "${mode_args[@]}"
  -e SKILLS_EVALS_IN_CONTAINER=1
  -e CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC=1
  --mount "type=bind,src=$repo_root,dst=/src,readonly"
  --mount "type=bind,src=$results_dir,dst=/results"
  ${context_mounts[@]+"${context_mounts[@]}"}
  ${git_mounts[@]+"${git_mounts[@]}"}
  -w /work
  "$image"
  bash -c 'cp -a /src /work/skills-evals && cd /work/skills-evals && exec python3 scripts/local_eval.py "$@" --container-token --results-dir /results'
  _ "$@")

# In the background, so a TERM during a long run reaches the trap at once
# (bash would otherwise hold it until the foreground command ended).
"${runner_cmd[@]}" &
status=0
wait "$!" || status=$?
exit "$status"
