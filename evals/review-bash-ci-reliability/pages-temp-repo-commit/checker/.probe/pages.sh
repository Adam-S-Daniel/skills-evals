#!/usr/bin/env bash
# Run the workflow's publish step for one named case in a throwaway clone
# with a local bare remote and its own HOME, and exit 0 only when its exit
# code, the remote's gh-pages branch and the global git config are right.
set -uo pipefail

case_name=${1:?usage: pages.sh CASE}
case "$case_name" in
    fresh-runner | signing-on-runner | developer-config-untouched | \
    build-failure-fails-the-job) ;;
    *) echo "unknown case: ${case_name}" >&2; exit 2 ;;
esac

work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT

# A copy of the final workspace, without this probe, any git state or a
# stale build.
mkdir "$work/repo"
cp -a . "$work/repo/"
rm -rf "$work/repo/.probe" "$work/repo/.git" "$work/repo/public"

# No identity may leak in from the environment: only the HOME config below.
unset GIT_AUTHOR_NAME GIT_AUTHOR_EMAIL GIT_COMMITTER_NAME GIT_COMMITTER_EMAIL EMAIL
export HOME="$work/home" GIT_CONFIG_NOSYSTEM=1 GIT_TERMINAL_PROMPT=0
unset XDG_CONFIG_HOME
mkdir "$HOME"
seed_git() { git -c user.name=seed -c user.email=seed@example.com -c commit.gpgsign=false "$@"; }

git init -q --bare "$work/remote.git"
cd "$work/repo" || exit 3
git init -q -b main
seed_git add -A
seed_git commit -q -m "seed"
git remote add origin "$work/remote.git"
git push -q origin main || exit 3
main_before=$(git --git-dir="$work/remote.git" rev-parse main)
source_rev=$(git rev-parse --short HEAD)

# The runner's global config. A hosted runner has no global identity, and
# git there cannot guess one; `user.useConfigOnly` makes this machine behave
# the same way instead of guessing from its host name.
runner_config='[init]\n\tdefaultBranch = main\n[user]\n\tuseConfigOnly = true\n'
case "$case_name" in
    fresh-runner)
        printf '%b' "$runner_config" > "$HOME/.gitconfig" ;;
    signing-on-runner)
        printf '%b' "$runner_config" > "$HOME/.gitconfig"
        printf '[commit]\n\tgpgsign = true\n[gpg]\n\tprogram = false\n' >> "$HOME/.gitconfig" ;;
    developer-config-untouched)
        # A maintainer's own machine: a global identity of their own.
        printf '[init]\n\tdefaultBranch = main\n[user]\n\tname = Robin Example\n\temail = robin@example.com\n' \
            > "$HOME/.gitconfig" ;;
    build-failure-fails-the-job)
        printf '%b' "$runner_config" > "$HOME/.gitconfig"
        printf '#!/usr/bin/env bash\necho "build failed" >&2\nexit 3\n' > scripts/build-site.sh ;;
esac
config_before=$(cat "$HOME/.gitconfig")

bash scripts/publish-pages.sh > "$work/out" 2>&1
code=$?
cat "$work/out"

remote_git() { git --git-dir="$work/remote.git" "$@"; }
published() {  # gh-pages holds the built site as one root commit, main is untouched
    local tip
    tip=$(remote_git rev-parse --verify -q refs/heads/gh-pages) || return 1
    [[ -z "$(remote_git rev-list --parents -n 1 "$tip" | cut -s -d' ' -f2)" ]] \
        && [[ "$(remote_git log -1 --format=%s "$tip")" == "handbook ${source_rev}" ]] \
        && remote_git cat-file -e "$tip:.nojekyll" \
        && remote_git show "$tip:index.html" | grep -q 'href="on-call.html"' \
        && remote_git show "$tip:onboarding.html" | grep -q 'Pair with a teammate' \
        && [[ "$(remote_git rev-parse main)" == "$main_before" ]]
}
nothing_published() { ! remote_git rev-parse --verify -q refs/heads/gh-pages >/dev/null; }

case "$case_name" in
    fresh-runner | signing-on-runner)
        [[ "$code" -eq 0 ]] && published ;;
    developer-config-untouched)
        [[ "$code" -eq 0 ]] && published \
            && [[ "$(cat "$HOME/.gitconfig")" == "$config_before" ]] ;;
    build-failure-fails-the-job)
        [[ "$code" -ne 0 ]] && nothing_published ;;
esac
