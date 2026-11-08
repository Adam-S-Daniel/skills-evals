# This repository's own agent-checks (see .githooks/agent-checks).
local_checks() {
  local f
  # Debug prints in src/ have shipped before.
  while IFS= read -r f; do
    case "$f" in
      src/*.py)
        if [ -f "$f" ] && grep -qE '^\s*print\(' "$f"; then
          fail "$f: debug print() in src/"
        fi ;;
    esac
  done <<<"$STAGED"
}
