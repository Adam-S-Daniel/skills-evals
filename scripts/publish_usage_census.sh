#!/usr/bin/env bash
# Publish the usage census (models and skills) to the `persistent/eval-results`
# branch.
#
# Runs on the OWNER'S DURABLE MACHINE, never in CI or a cloud session: the
# census reads local Claude Code transcripts (~/.claude/projects), which
# those surfaces do not have. See evals/usage/CENSUS.md for what it is, the
# privacy contract on its output, and how to schedule this script.
#
# Steps, all inside one temp dir that is removed on exit:
#   0. shallow-clone the private `persistent/usage-events` branch (step 5
#      reuses the clone) so the census can read the cloud guidance records in
#      it, read-only (`--cloud-guidance`);
#   1. shallow-clone skills-evals and run ITS copy of
#      scripts/model_usage_census.py against the real transcripts; with the
#      private branch read (or known missing), the census also writes a
#      PRIVATE plan of this run's loaded skill copies (#562, 2026-11-02);
#   1b. clone, bare and blob-less, only the public registries that plan names
#      (anonymously: no credential helper, no global or system config, no
#      prompt) and add the plan's `skill-digest` rows: a 12-hex prefix only
#      for content once on a public branch there. A failed clone leaves those
#      rows `unknown:unverified-commit` and the summary says
#      "registry: not read", never which one or why;
#   2. with the persistent/eval-results branch (shallow-cloned before step 1,
#      so the census can read its coverage/latest.json), copy in usage/latest.json
#      (models) and usage/weekly-local.json (skill invocations), after
#      skill_usage.check_public passes on the weekly file (a full digest, a
#      commit, a fork's name or a private skill's name refuses the publish);
#   3. commit "propagation: usage census [skip ci]" ONLY if the census
#      changed (either file), and push it (one `pull --rebase` retry when
#      the push is not a fast-forward);
#   4. verify with `git merge-base --is-ancestor HEAD origin/persistent/eval-results` —
#      a push that printed success is not proof the commit is on the branch;
#   5. then, and only then, publish the PRIVATE per-invocation records
#      (`--events-out`) to the `persistent/usage-events` branch of the private
#      adam-agentskills-private repository: merged by id into
#      events/<YYYY-MM>/<machine>.jsonl, committed only if something was
#      added, pushed and verified the same way. A missing branch is created
#      as an orphan with a README. A failure here never undoes or blocks the
#      public publish: it prints one line without detail and the script exits
#      1 at the end.
# A failed fetch in step 0 (the repository does not answer, or the clone
# fails; a branch that does not exist is not a failure) never blocks the
# public publish either: once the results clone exists, the previous public
# usage/weekly-local.json's cloud rows and cloud source, and its local and
# cloud skill-digest rows, each with its source (#562), are carried forward
# verbatim (they are already public), each unless its source was read more
# than 14 days ago; the summary says "cloud: carried forward", "skill copies:
# carried forward" and "cloud skill copies: carried forward" (or "not read"),
# and the script exits 1 at the end like a private failure.
#
# Transcript roots: ~/.claude/projects, and under WSL also every existing
# Windows-side root (/mnt/c/Users/*/.claude/projects) and every Cowork root
# below /mnt/c/Users/*/AppData/Local/Claude-Data/*/local-agent-mode-sessions.
# Hook logs: agent-checks' default path, and under WSL the Windows-side
# /mnt/c/Users/*/.local/state/agent-checks/runs.jsonl files that exist.
#
# Credentials: whatever git already has on this machine. This script handles
# no token and reads no secret.
#
# Usage: scripts/publish_usage_census.sh [--dry-run]
#   --dry-run   do everything except push
#
# Output: one summary line — totals only, no model ids, no skill names, no
# paths, never a private record's content.
#
# Test seams (all optional; the defaults are the real thing):
#   SKILLS_EVALS_URL  where to clone from (default: the GitHub repo)
#   CENSUS_PROJECTS   transcript root(s), `:`-separated; replaces every default root
#   CENSUS_NOW        ISO-8601 instant handed to the census as `--now`
#   USAGE_HOOK_LOGS   hook log path(s), `:`-separated; replaces the defaults
#   USAGE_EVENTS_URL  the private repository to publish events to
#   REGISTRY_MIRROR_BASE  prefix of a public registry's clone URL, before
#                     `<owner>/<repo>.git` (default https://github.com/)
#   WSL_USERS_DIR     the Windows users directory seen from WSL (default /mnt/c/Users)
#   PYTHON            interpreter (default python3)
set -euo pipefail

URL="${SKILLS_EVALS_URL:-https://github.com/Adam-S-Daniel/skills-evals.git}"
BRANCH="persistent/eval-results"
EVENTS_URL="${USAGE_EVENTS_URL:-https://github.com/Adam-S-Daniel/adam-agentskills-private.git}"
EVENTS_BRANCH="persistent/usage-events"
MIRROR_BASE="${REGISTRY_MIRROR_BASE:-https://github.com/}"
WIN_USERS="${WSL_USERS_DIR:-/mnt/c/Users}"
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

tmp="$(mktemp -d "${TMPDIR:-/tmp}/usage-census-XXXXXXXX")"
trap 'rm -rf "$tmp"' EXIT

# The machine's git identity when it has one; a noreply fallback when it does
# not, so a fresh box can still commit.
ident=()
if [ -z "$(git config user.email 2>/dev/null || true)" ]; then
  ident=(-c user.name=usage-census -c user.email=usage-census@users.noreply.github.com)
fi

# Both clones are scratch, removed by the EXIT trap. `git commit` and `git
# fetch` would otherwise spawn a detached `git maintenance run --auto` that can
# still be writing into .git when `rm -rf "$tmp"` runs; the rm then fails and,
# under `set -e`, turns a successful publish into exit 1.
no_bg=(--config maintenance.auto=false --config gc.auto=0)

git clone "${no_bg[@]}" --quiet --depth 1 "$URL" "$tmp/src" >/dev/null 2>&1 \
  || { echo "usage census: could not clone skills-evals" >&2; exit 1; }

# --- 0. The private branch, fetched BEFORE the census so the census can read
# the cloud guidance records in it. private_fetch is `cloned`, `missing` (the
# repository answered and has no such branch) or `failed` (and then
# private_fetch_step names the step for the one-line failure message).
private_fetch=failed
private_fetch_step=reach
found=0
git ls-remote --exit-code --heads "$EVENTS_URL" "refs/heads/$EVENTS_BRANCH" >/dev/null 2>&1 \
  || found=$?
if [ "$found" = 0 ]; then
  if git clone "${no_bg[@]}" --quiet --depth 1 --single-branch --branch "$EVENTS_BRANCH" \
       "$EVENTS_URL" "$tmp/private" >/dev/null 2>&1; then
    private_fetch=cloned
  else
    private_fetch_step=clone
  fi
elif [ "$found" = 2 ]; then
  private_fetch=missing
fi

# The results branch, cloned BEFORE the census so the census can read the
# published coverage census in it (`--coverage-census`: a public registry's
# skill with no fixture yet is still a publishable name); step 2 reuses it.
git clone "${no_bg[@]}" --quiet --depth 1 --single-branch --branch "$BRANCH" "$URL" "$tmp/results" >/dev/null 2>&1 \
  || { echo "usage census: could not clone the $BRANCH branch" >&2; exit 1; }
coverage="$tmp/results/coverage/latest.json"
coverage_args=()
[ -f "$coverage" ] && coverage_args=(--coverage-census "$coverage")

is_wsl=0
if [ -n "${WSL_DISTRO_NAME:-}" ] || grep -qi microsoft /proc/version 2>/dev/null; then
  is_wsl=1
fi

census_args=(--out "$tmp/usage/latest.json" --weekly-out "$tmp/usage/weekly-local.json"
             --events-out "$tmp/events.jsonl")
if [ -n "${CENSUS_PROJECTS:-}" ]; then
  census_args+=(--projects "$CENSUS_PROJECTS")
elif [ "$is_wsl" = 1 ]; then
  # Desktop Code-tab and remote-control sessions write to the Windows root,
  # Cowork under Claude-Data; the census counts a session found twice once.
  census_args+=(--projects "$HOME/.claude/projects")
  shopt -s nullglob
  for dir in "$WIN_USERS"/*/.claude/projects; do
    [ -d "$dir" ] && census_args+=(--projects "$dir")
  done
  for base in "$WIN_USERS"/*/AppData/Local/Claude-Data/*/local-agent-mode-sessions; do
    [ -d "$base" ] || continue
    while IFS= read -r -d '' dir; do
      census_args+=(--projects "$dir")
    done < <(find "$base" -maxdepth 8 -type d -path '*/.claude/projects' -prune -print0 2>/dev/null)
  done
  shopt -u nullglob
fi
if [ -n "${USAGE_HOOK_LOGS+set}" ]; then
  hook_logs="$USAGE_HOOK_LOGS"
else
  hook_logs="${AGENT_CHECKS_LOG:-${XDG_STATE_HOME:-$HOME/.local/state}/agent-checks/runs.jsonl}"
  if [ "$is_wsl" = 1 ]; then
    shopt -s nullglob
    for log in "$WIN_USERS"/*/.local/state/agent-checks/runs.jsonl; do
      [ -f "$log" ] && hook_logs+=":$log"
    done
    shopt -u nullglob
  fi
fi
census_args+=(--hook-logs "$hook_logs")
census_args+=("${coverage_args[@]+"${coverage_args[@]}"}")
if [ -n "${CENSUS_NOW:-}" ]; then census_args+=(--now "$CENSUS_NOW"); fi
if [ "$private_fetch" = cloned ]; then census_args+=(--cloud-guidance "$tmp/private"); fi
# #562: the loaded copies need the store's record of each use; a branch that
# does not exist yet is an empty store (every use takes this run's record).
# A failed fetch passes nothing, so no skill-records source is written and the
# previous one is carried below.
plan=""
if [ "$private_fetch" = cloned ]; then
  plan="$tmp/digest-plan.json"
  census_args+=(--event-store "$tmp/private" --digest-plan-out "$plan")
elif [ "$private_fetch" = missing ]; then
  mkdir "$tmp/empty-store"
  plan="$tmp/digest-plan.json"
  census_args+=(--event-store "$tmp/empty-store" --digest-plan-out "$plan")
fi
# The census's own status line names its output path; this script prints its
# own summary instead. stderr stays: its messages name no path.
"$PY" "$tmp/src/scripts/model_usage_census.py" "${census_args[@]}" >/dev/null

# --- 1b. The public registries the plan's uses point at, cloned bare and
# blob-less (adamdaniel.ai is about 529 MiB in full; trees are enough to list
# a path's history, and `git archive` fetches only that path's blobs). Every
# git here runs without the machine's global or system config, without a
# credential helper and without a prompt: these repositories are public, and
# a clone that needs a credential has failed. Errors are discarded, so no
# path, URL or sha reaches the output; only the fixed note does.
registry_note=""
if [ -n "$plan" ]; then
  mirror_args=()
  unread=0
  n=0
  while IFS= read -r repo; do
    [ -n "$repo" ] || continue
    if ! [[ "$repo" =~ ^[A-Za-z0-9][A-Za-z0-9-]*/[A-Za-z0-9._-]+$ ]]; then
      unread=1
      continue
    fi
    n=$((n + 1))
    url="$MIRROR_BASE$repo.git"
    if env GIT_CONFIG_GLOBAL=/dev/null GIT_CONFIG_NOSYSTEM=1 GIT_TERMINAL_PROMPT=0 \
         git -c credential.helper= clone "${no_bg[@]}" --quiet --bare --filter=blob:none \
         -- "$url" "$tmp/mirror-$n" >/dev/null 2>&1 \
       && [ "$(env GIT_CONFIG_GLOBAL=/dev/null GIT_CONFIG_NOSYSTEM=1 \
               git -C "$tmp/mirror-$n" config --get remote.origin.url 2>/dev/null)" = "$url" ]; then
      mirror_args+=("$repo=$tmp/mirror-$n")
    else
      unread=1
    fi
  done < <("$PY" -c 'import json, sys; print("\n".join(json.load(open(sys.argv[1]))["registries"]))' "$plan")
  applied="$("$PY" - "$tmp/src/scripts" "$plan" "$tmp/usage/weekly-local.json" \
               "${mirror_args[@]+"${mirror_args[@]}"}" 2>/dev/null <<'PY'
import sys
sys.path.insert(0, sys.argv[1])
import model_usage_census
mirrors = dict(arg.split("=", 1) for arg in sys.argv[4:])
print("unread" if model_usage_census.apply_digest_plan(sys.argv[2], sys.argv[3], mirrors)
      else "read")
PY
  )" || { echo "usage census: loaded copies could not be added" >&2; exit 1; }
  if [ "$unread" = 1 ] || [ "$applied" = unread ]; then registry_note="registry: not read"; fi
fi

# A failed fetch of the private branch: carry the previous public file's cloud
# guidance rows and local and cloud skill-digest rows, each with its source,
# into this run's file (skill_usage.carry), so the publish below goes ahead
# with them instead of dropping what is already public. Decided here because
# the previous file is in the results clone. One fixed phrase per carried part.
cloud_note=""
if [ "$private_fetch" = failed ]; then
  cloud_note="$("$PY" - "$tmp/src/harness" "$tmp/results/usage/weekly-local.json" \
               "$tmp/usage/weekly-local.json" "$tmp/src/scripts" <<'PY'
import json, sys
sys.path.insert(0, sys.argv[1])
sys.path.insert(0, sys.argv[4])
import skill_usage
import model_usage_census
from pathlib import Path
new = json.load(open(sys.argv[3], encoding="utf-8"))
carried = skill_usage.carry(skill_usage.load(sys.argv[2]), new)
if any(count is not None for count in carried.values()):
    model_usage_census._write_json(Path(sys.argv[3]), new)
print("; ".join(f"{label}: " + ("not read" if count is None else "carried forward")
                for label, count in carried.items()))
PY
  )" || cloud_note="cloud: not read; skill copies: not read; cloud skill copies: not read"
fi

# The last gate on the public weekly file (#562): nothing is staged when it
# fails, and the line names no value.
"$PY" - "$tmp/src/harness" "$tmp/src/scripts" "$tmp/usage/weekly-local.json" "$tmp/src" \
  "$coverage" >/dev/null 2>&1 <<'PY' || { echo "usage census: refusing to publish (check_public)" >&2; exit 1; }
import json, sys
from pathlib import Path
sys.path.insert(0, sys.argv[1])
sys.path.insert(0, sys.argv[2])
import model_usage_census
import skill_usage
doc = json.load(open(sys.argv[3], encoding="utf-8"))
allowlist = model_usage_census.skill_allowlist(Path(sys.argv[4]), Path(sys.argv[5]))
public = set(model_usage_census.public_registries().values())
sys.exit(1 if skill_usage.check_public(doc, allowlist, public) else 0)
PY

# Totals for the summary line, and the changed/unchanged decision. Both read
# only the four JSON files; neither uses the clock. A missing old
# weekly-local.json (the first run after it was added) reads as changed. Its
# `to` and `sessions_scanned` move on every run, so only its rows and window
# start are compared.
decision="$("$PY" - "$tmp/usage" "$tmp/results/usage" "$REFRESH_DAYS" "$tmp/events.jsonl" <<'PY'
import json, os, sys
from datetime import datetime

new_dir, old_dir, refresh_days = sys.argv[1], sys.argv[2], int(sys.argv[3])
with open(sys.argv[4], encoding="utf-8") as f:
    events = sum(1 for line in f if line.strip())
def load(folder, name):
    return json.load(open(os.path.join(folder, name), encoding="utf-8"))
new, new_weekly = load(new_dir, "latest.json"), load(new_dir, "weekly-local.json")
turns = sum(sum(w.values()) for w in new["counts"].values())
calls = sum(r["invocations"] for r in new_weekly["rows"] if r["kind"] == "skill")
hooks = sum(r["invocations"] for r in new_weekly["rows"]
            if r["kind"] == "hook" and r["name"] == "all")
models = len(new["counts"])
state = "changed"
try:
    old, old_weekly = load(old_dir, "latest.json"), load(old_dir, "weekly-local.json")
    stamp = "%Y-%m-%dT%H:%M:%SZ"
    age = (datetime.strptime(new["generated_at"], stamp)
           - datetime.strptime(old["generated_at"], stamp))
    if (old.get("counts") == new["counts"] and old.get("weeks") == new["weeks"]
            and old_weekly.get("rows") == new_weekly["rows"]
            and [s.get("from") for s in old_weekly.get("sources")]
                == [s["from"] for s in new_weekly["sources"]]
            and 0 <= age.total_seconds() < refresh_days * 86400):
        state = "unchanged"
except (OSError, ValueError, KeyError, TypeError, AttributeError):
    pass
print(f"{state} {models} {turns} {calls} {hooks} {len(new['weeks'])} {events}")
PY
)"
read -r state models turns calls hooks weeks events <<<"$decision"

summary="usage census: $models models, $turns assistant turns, $calls skill invocations, $hooks hook runs, $weeks weeks"
if [ -n "$cloud_note" ]; then summary="$summary; $cloud_note"; fi
if [ -n "$registry_note" ]; then summary="$summary; $registry_note"; fi

# --- 1. The public census. A failure here exits at once: the private
# publish below is never reached without a public result.
if [ "$state" = "unchanged" ]; then
  public_note="unchanged, nothing published"
else
  mkdir -p "$tmp/results/usage"
  cp "$tmp/usage/latest.json" "$tmp/results/usage/latest.json"
  cp "$tmp/usage/weekly-local.json" "$tmp/results/usage/weekly-local.json"
  git -C "$tmp/results" add usage/latest.json usage/weekly-local.json
  # Only these two paths may be committed; either alone is fine (a file whose
  # bytes did not move is not staged), anything else or nothing is refused.
  staged="$(git -C "$tmp/results" diff --cached --name-only)"
  case "$staged" in
    usage/latest.json | usage/weekly-local.json | "usage/latest.json"$'\n'"usage/weekly-local.json") ;;
    *)
      echo "usage census: unexpected staged paths; refusing to commit" >&2
      exit 1
      ;;
  esac
  git -C "$tmp/results" "${ident[@]+"${ident[@]}"}" commit --quiet \
    -m "propagation: usage census [skip ci]" >/dev/null

  if [ "$dry_run" = 1 ]; then
    public_note="dry run, committed locally and pushed nothing"
  else
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
    public_note="published"
  fi
fi

# --- 2. The private per-invocation records. Every step is checked by hand
# (a function called under `||` runs without `set -e`), and every failure
# returns 1 after one line that names the step and nothing else.
private_fail() { echo "usage census: private events not published ($1)" >&2; return 1; }

publish_private() {
  local dir="$tmp/private" created=0 added
  if [ "$private_fetch" = cloned ]; then
    :  # fetched before the census, which has only read it
  elif [ "$private_fetch" = missing ]; then
    # The repository answered and has no such branch: (re)create it.
    git init --quiet -b "$EVENTS_BRANCH" "$dir" >/dev/null 2>&1 \
      && git -C "$dir" config maintenance.auto false \
      && git -C "$dir" config gc.auto 0 \
      && git -C "$dir" remote add origin "$EVENTS_URL" \
      || { private_fail "create"; return 1; }
    cat > "$dir/README.md" <<'README' || { private_fail "create"; return 1; }
# Private usage events

Data, not code. One JSON line per skill invocation and per local git-hook
run, written by skills-evals' `scripts/publish_usage_census.sh` on the
owner's machine into `events/<YYYY-MM>/<machine>.jsonl`, merged by `id`.
Field reference: skills-evals `evals/usage/CENSUS.md`, "Private usage events".

- **Private.** The records carry timestamps, session ids and titles,
  repositories and branches. Only weekly counts are public (skills-evals'
  `persistent/eval-results` branch, `usage/weekly-local.json`).
- **Regenerable for the last 8 weeks only.** The publisher re-creates this
  branch when it is missing, from the transcripts and hook logs still on the
  machine, which covers the census window. Anything older exists only here.
- **No ruleset.** This repository is private, and rulesets cannot protect a
  branch of it on this plan, so nothing guards it against deletion or a force
  push. Do not delete it.
- cloud-* files and the shards under events/<month>/cloud-skills/ are written by cloud hooks and cannot be regenerated; a re-created branch loses them.
- A cloud-skills shard holds one line per skill use a cloud session uploaded, from its main transcript and subagent transcripts: records seen, never complete.
README
    created=1
  else
    private_fail "$private_fetch_step"
    return 1
  fi
  added="$("$PY" - "$tmp/src/scripts" "$tmp/events.jsonl" "$dir" 2>/dev/null <<'PY'
import sys
sys.path.insert(0, sys.argv[1])
import model_usage_census
print(model_usage_census.merge_events(sys.argv[2], sys.argv[3]))
PY
)" || { private_fail "merge"; return 1; }
  git -C "$dir" add -A >/dev/null 2>&1 || { private_fail "stage"; return 1; }
  local path staged
  staged="$(git -C "$dir" diff --cached --name-only)" || { private_fail "stage"; return 1; }
  # Only event files may be committed, plus the README on creation; never
  # anything else (and so never anything under lessons/).
  while IFS= read -r path; do
    [ -n "$path" ] || continue
    # cloud-* files, and the per-session shards under cloud-skills/
    # (#562 PR B), belong to cloud hooks; this machine never writes one.
    if [[ "$path" =~ ^events/[0-9]{4}-[0-9]{2}/cloud-[^/]*(/[0-9a-f]{16})?\.jsonl$ ]]; then
      private_fail "unexpected staged paths"
      return 1
    fi
    if [[ "$path" =~ ^events/[0-9]{4}-[0-9]{2}/[A-Za-z0-9][A-Za-z0-9._-]*\.jsonl$ ]]; then
      continue
    fi
    if [ "$created" = 1 ] && [ "$path" = "README.md" ]; then
      continue
    fi
    private_fail "unexpected staged paths"
    return 1
  done <<<"$staged"
  if [ -z "$staged" ]; then
    private_note="0 new of $events"
    return 0
  fi
  git -C "$dir" "${ident[@]+"${ident[@]}"}" commit --quiet -m "usage events [skip ci]" \
    >/dev/null 2>&1 || { private_fail "commit"; return 1; }
  if [ "$dry_run" = 1 ]; then
    private_note="$added new of $events, dry run"
    return 0
  fi
  if ! git -C "$dir" push --quiet origin "HEAD:refs/heads/$EVENTS_BRANCH" >/dev/null 2>&1; then
    git -C "$dir" "${ident[@]+"${ident[@]}"}" pull --rebase --quiet origin "$EVENTS_BRANCH" \
      >/dev/null 2>&1 || { private_fail "rebase"; return 1; }
    git -C "$dir" push --quiet origin "HEAD:refs/heads/$EVENTS_BRANCH" >/dev/null 2>&1 \
      || { private_fail "push"; return 1; }
  fi
  git -C "$dir" fetch --quiet origin "$EVENTS_BRANCH" >/dev/null 2>&1 \
    || { private_fail "verify"; return 1; }
  git -C "$dir" merge-base --is-ancestor HEAD FETCH_HEAD >/dev/null 2>&1 \
    || { private_fail "verify"; return 1; }
  private_note="$added new of $events"
  [ "$created" = 0 ] || private_note="$private_note, branch created"
  return 0
}

private_note="not published"
private_rc=0
publish_private || private_rc=$?

echo "$summary; $public_note; private events: $private_note"
exit "$private_rc"
