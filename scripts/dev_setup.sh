#!/usr/bin/env bash
# Install what .github/workflows/ci.yml's `test` job installs, so a fresh
# machine or cloud session can run this repo's tests. ci.yml is the source of
# truth: test/issues/test_issue_dev_setup.py fails when the two lists drift.
# The script never uses sudo and does not install bubblewrap (bwrap).
#
#   bash scripts/dev_setup.sh                  install everything
#   bash scripts/dev_setup.sh --print-pins     list the pip pins, install nothing
#   bash scripts/dev_setup.sh --print-npm-dirs list the npm dirs, install nothing
#   bash scripts/dev_setup.sh --print-bundler-dirs list the Gemfile dirs, install nothing
#   bash scripts/dev_setup.sh --print-git-pin  print GIT_MIN, GIT_PIN and GIT_PIN_SHA256
#   bash scripts/dev_setup.sh --check-git      exit 0 when `git` is GIT_MIN or later
#   bash scripts/dev_setup.sh --build-git PREFIX
#                                              build and install the pinned Git into PREFIX
#
# Git: config-based hooks, the way the fleet installs its hooks
# (adam-agentskills ADR 0020), need Git 2.54 or later, and eval arms will run
# the fleet hooks (ADR 0012's fleet hooks addendum, skills-evals#535).
# ci.yml's suite runs --check-git (the runner image ships a newer Git). The
# default install never builds Git: it warns, as it does for bwrap, and
# --build-git builds the pinned release from kernel.org's tarball, verified
# by its sha256 (kernel.org's signed sha256sums.asc), into a prefix the caller
# can write: /usr/local in the routine container, which runs as root, or
# "$HOME/.local" without root. Building needs a C compiler, make, and the
# zlib, OpenSSL and libcurl headers.
set -euo pipefail

GIT_MIN=2.54
GIT_PIN=2.56.0
GIT_PIN_SHA256=26c56c296b38c0695b26fa95f475f1d01704d2d38e73465ca30b0b2f5dc789d3
GIT_PIN_URL="https://mirrors.edge.kernel.org/pub/software/scm/git/git-${GIT_PIN}.tar.xz"

PIP_PINS=(
  pyyaml==6.0.3
  markdown-it-py==4.2.0
  tree-sitter==0.26.0
  tree-sitter-bash==0.25.1
  pytest==9.1.1
  pytest-xdist==3.8.0
)

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# The real-work fixtures' directories come from their own `deps:` entries,
# as ci.yml's install steps read them (scaffold_real_work.py deps-dirs, which
# needs PyYAML). Gemfile directories are installed frozen into vendor/bundle
# beside the Gemfile, as ci.yml's "Install real-work fixture gems" step does.
real_work_dirs() {
  local listed
  listed="$(python3 "$REPO_ROOT/scripts/scaffold_real_work.py" deps-dirs --manager "$1")" || return 1
  local dir
  for dir in $listed; do
    printf 'evals/real-work/%s\n' "$dir"
  done
}

# Whether `git` on PATH (the one an eval arm runs) is GIT_MIN or later.
git_new_enough() {
  local version
  version="$(git --version 2>/dev/null)" || return 1
  awk -v min="$GIT_MIN" '
    BEGIN { split(min, m, ".") }
    $1 == "git" && $2 == "version" && match($3, /^[0-9]+\.[0-9]+/) {
      split(substr($3, 1, RLENGTH), v, ".")
      ok = (v[1] + 0 > m[1] + 0) || (v[1] + 0 == m[1] + 0 && v[2] + 0 >= m[2] + 0)
      exit !ok
    }
    { exit 1 }' <<<"$version"
}

git_too_old_message() {
  echo "dev_setup: Git $GIT_MIN or later not found (\`git --version\`: $(git --version 2>/dev/null || echo unreadable)); config-based hooks need it, so a fixture with \`fleet_hooks: true\` is refused. Build the pinned Git $GIT_PIN with: bash scripts/dev_setup.sh --build-git \"\$HOME/.local\" (then put \$HOME/.local/bin first on PATH)."
}

build_git() {
  local prefix="$1"
  case "$prefix" in
    /*) ;;
    *) echo "dev_setup: --build-git needs an absolute PREFIX" >&2; return 2 ;;
  esac
  work="$(mktemp -d)"
  trap 'rm -rf "$work"' EXIT
  curl -fsSL --proto '=https' --tlsv1.2 -o "$work/git.tar.xz" "$GIT_PIN_URL"
  printf '%s  %s\n' "$GIT_PIN_SHA256" "$work/git.tar.xz" | sha256sum -c --quiet -
  mkdir "$work/src"
  tar -xJf "$work/git.tar.xz" -C "$work/src" --strip-components=1 --no-same-owner
  make -C "$work/src" -j"$(nproc)" prefix="$prefix" sysconfdir=/etc \
    NO_GETTEXT=1 NO_TCLTK=1 NO_PERL=1 NO_PYTHON=1 NO_RUST=1 install >/dev/null
  echo "dev_setup: installed $("$prefix/bin/git" --version) into $prefix"
}

USAGE="usage: dev_setup.sh [--print-pins | --print-npm-dirs | --print-bundler-dirs | --print-git-pin | --check-git | --build-git PREFIX]"
if [ "$#" -eq 2 ] && [ "$1" = --build-git ]; then
  build_git "$2"
  exit 0
fi
if [ "$#" -gt 1 ]; then
  echo "$USAGE" >&2
  exit 2
fi
if [ "$#" -eq 1 ]; then
  case "$1" in
    --print-pins) printf '%s\n' "${PIP_PINS[@]}"; exit 0 ;;
    --print-npm-dirs) echo evals/browser-testing/seed; real_work_dirs npm; exit 0 ;;
    --print-bundler-dirs) real_work_dirs bundler; exit 0 ;;
    --print-git-pin) printf '%s\n' "$GIT_MIN" "$GIT_PIN" "$GIT_PIN_SHA256"; exit 0 ;;
    --check-git)
      if git_new_enough; then
        echo "dev_setup: $(git --version) is Git $GIT_MIN or later"
        exit 0
      fi
      git_too_old_message >&2
      exit 1 ;;
    *) echo "$USAGE" >&2; exit 2 ;;
  esac
fi

# A PEP 668 "externally managed" Python refuses the first form.
if ! python3 -m pip install "${PIP_PINS[@]}"; then
  python3 -m pip install --break-system-packages "${PIP_PINS[@]}"
fi

npm_dirs="$(real_work_dirs npm)"
for dir in evals/browser-testing/seed $npm_dirs; do
  (cd "$REPO_ROOT/$dir" && npm ci --ignore-scripts --no-audit --no-fund)
done

bundler_dirs="$(real_work_dirs bundler)"
for dir in $bundler_dirs; do
  (cd "$REPO_ROOT/$dir" && BUNDLE_PATH=vendor/bundle BUNDLE_FROZEN=true BUNDLE_DISABLE_SHARED_GEMS=true BUNDLE_APP_CONFIG="$(mktemp -d)" BUNDLE_SILENCE_ROOT_WARNING=true bundle install --quiet)
done

if ! git_new_enough; then
  git_too_old_message >&2
fi

if ! command -v bwrap >/dev/null 2>&1; then
  echo "dev_setup: bubblewrap (bwrap) not found; tests of workspace-executing scorers fail closed without it. CI installs it; see .github/workflows/ci.yml." >&2
fi

echo "dev_setup: done."
echo "Run one module:  python3 -m pytest test/issues/<file>.py -q -n 2      Full suite:  python3 test/run_tests.py --jobs auto"
