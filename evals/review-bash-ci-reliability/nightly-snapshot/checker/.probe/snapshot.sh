#!/usr/bin/env bash
# Run the workflow's publish step for one named case in a throwaway git repo
# with a local bare remote, and exit 0 only when its exit code, output and
# resulting history are right.
set -uo pipefail

case_name=${1:?usage: snapshot.sh CASE}
case "$case_name" in
    signing-on-runner | no-change-night | missing-tool-not-silent | \
    new-data-committed | build-failure-fails-the-job) ;;
    *) echo "unknown case: ${case_name}" >&2; exit 2 ;;
esac

probe=$(cd "$(dirname "$0")" && pwd)
work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT

# A copy of the final workspace, without this probe or any git state.
mkdir "$work/repo"
cp -a . "$work/repo/"
rm -rf "$work/repo/.probe" "$work/repo/.git"

export HOME="$work/home" GIT_CONFIG_NOSYSTEM=1 GIT_TERMINAL_PROMPT=0
mkdir "$HOME"
printf '[init]\n\tdefaultBranch = main\n' > "$HOME/.gitconfig"
seed_git() { git -c user.name=seed -c user.email=seed@example.com -c commit.gpgsign=false "$@"; }

git init -q --bare "$work/remote.git"
cd "$work/repo" || exit 3
git init -q -b main
seed_git add -A
seed_git commit -q -m "seed"
git remote add origin "$work/remote.git"
git push -q origin main || exit 3
before=$(git rev-parse HEAD)

with_tool=$probe/bin:$PATH
without_tool=$(tr ':' '\n' <<<"$PATH" | while read -r dir; do
    [[ -n "$dir" && ! -x "$dir/dasel" ]] && printf '%s:' "$dir"; done)
without_tool=${without_tool%:}
run_path=$with_tool

new_data() { printf 'east,2026-10-03,11\n' >> data/east.csv; }

case "$case_name" in
    signing-on-runner)
        new_data
        printf '[commit]\n\tgpgsign = true\n[gpg]\n\tprogram = false\n' >> "$HOME/.gitconfig" ;;
    no-change-night) ;;
    missing-tool-not-silent)
        new_data; run_path=$without_tool ;;
    new-data-committed)
        new_data ;;
    build-failure-fails-the-job)
        new_data
        printf '#!/usr/bin/env bash\necho "build failed" >&2\nexit 3\n' > scripts/build-snapshot.sh ;;
esac

out=$(PATH=$run_path bash scripts/publish-snapshot.sh 2>&1)
code=$?
has() { grep -qE -- "$1" <<<"$out"; }
subject=$(git log -1 --format=%s 2>/dev/null)
remote_subject=$(git --git-dir="$work/remote.git" log -1 --format=%s main 2>/dev/null)
committed() {  # the new snapshot is HEAD here and on the remote, with the version
    [[ "$(git rev-parse HEAD)" != "$before" ]] \
        && [[ "$subject" == "snapshot 1.4.2" && "$remote_subject" == "snapshot 1.4.2" ]] \
        && git show HEAD:snapshot/all.csv | grep -qx 'east,2026-10-03,11'
}
unchanged() { [[ "$(git rev-parse HEAD)" == "$before" ]]; }

case "$case_name" in
    signing-on-runner | new-data-committed)
        [[ "$code" -eq 0 ]] && committed ;;
    no-change-night)
        [[ "$code" -eq 0 ]] && unchanged ;;
    missing-tool-not-silent)
        # Either the version is still found without dasel, or the job fails
        # and says dasel is the reason. Never a commit naming no version.
        [[ "$(git log --format=%s | grep -c unknown)" -eq 0 ]] \
            && { { [[ "$code" -eq 0 ]] && committed; } \
                 || { [[ "$code" -ne 0 ]] && unchanged && has 'dasel'; }; } ;;
    build-failure-fails-the-job)
        [[ "$code" -ne 0 ]] && unchanged ;;
esac
