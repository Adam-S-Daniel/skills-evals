#!/usr/bin/env bash
# Install an exact Claude Code release from npm and prove the `claude` on PATH
# works and is that release, retrying with exponential backoff inside an
# overall time limit.
#
# Usage: install_claude_code.sh MAJOR.MINOR.PATCH
#
# Why it exists: run 41670633700 installed Claude Code and `claude --version`
# printed "Error: claude native binary not installed." (npm left no native
# binary). A second install fixed it, so the workflows retry instead of
# failing the whole eval on a one-off.
#
# Attempt 1 is `npm install -g`; every later attempt adds `--force` so npm
# reinstalls over a half-written package. An attempt succeeds only when
# `timeout -k 10 60 claude --version` exits 0 and its first token is the
# requested version. Delays between attempts are 5, 10, 20, 40 and 80 seconds,
# and the whole thing is bounded by LIMIT seconds measured from the first
# install: no attempt starts if its delay would reach the limit, and each
# command is bounded by what remains.
#
# Tests inject the sleep and the clock (never read in a test run):
#   SLEEP_CMD  command that sleeps its argument (default: sleep)
#   NOW_CMD    command that prints epoch seconds (default: date +%s)
set -euo pipefail

latest="${1:-}"
[[ "$latest" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]] || {
  echo "::error::install_claude_code.sh needs a plain MAJOR.MINOR.PATCH version"
  exit 2
}

LIMIT=180
delays=(5 10 20 40 80)
read -r -a sleep_cmd <<<"${SLEEP_CMD:-sleep}"
read -r -a now_cmd <<<"${NOW_CMD:-date +%s}"

errf="$(mktemp)"
trap 'rm -f "$errf"' EXIT
start="$("${now_cmd[@]}")"
elapsed() { echo $(("$("${now_cmd[@]}")" - start)); }

last_error=""
note_error() {
  # First line only, printable characters only, bounded: this lands in a
  # workflow command, so it must not carry a newline.
  local line="${1%%$'\n'*}"
  line="${line//[^[:print:]]/}"
  last_error="${line:0:200}"
}

attempt_once() {
  local n="$1" args=(-g) out rc=0 remaining vt
  ((n > 1)) && args+=(--force)
  remaining=$((LIMIT - $(elapsed)))
  ((remaining >= 1)) || remaining=1
  out="$(timeout -k 10 "$remaining" npm install "${args[@]}" "@anthropic-ai/claude-code@${latest}" 2>&1)" || rc=$?
  if ((rc != 0)); then
    note_error "${out:-npm install exited ${rc}}"
    return 1
  fi
  hash -r
  vt=$((LIMIT - $(elapsed)))
  ((vt >= 1)) || vt=1
  ((vt <= 60)) || vt=60
  rc=0
  # stdout alone is the version; stderr (update notices, warnings) stays out
  # of it and is only read to explain a failure.
  out="$(timeout -k 10 "$vt" claude --version 2>"$errf")" || rc=$?
  if ((rc != 0)); then
    [[ -n "$out" ]] || out="$(<"$errf")"
    note_error "${out:-claude --version exited ${rc}}"
    return 1
  fi
  # First line only, and only characters a version string needs.
  local first="${out%%$'\n'*}"
  first="${first:0:80}"
  first="${first//[^A-Za-z0-9._() -]/}"
  if [[ "${first%% *}" != "$latest" ]]; then
    note_error "claude --version reported '${first}', expected ${latest}"
    return 1
  fi
  return 0
}

attempt=0
while :; do
  attempt=$((attempt + 1))
  if attempt_once "$attempt"; then
    echo "Claude Code ${latest} installed and verified on attempt ${attempt} ($(elapsed)s)"
    exit 0
  fi
  idx=$((attempt - 1))
  ((idx < ${#delays[@]})) || break
  delay="${delays[idx]}"
  (($(elapsed) + delay < LIMIT)) || break
  echo "attempt ${attempt} failed (${last_error}); retrying in ${delay}s"
  "${sleep_cmd[@]}" "$delay"
done

echo "::error::Claude Code ${latest} did not install a working claude after ${attempt} attempts in $(elapsed) seconds (last error: ${last_error})"
exit 1
