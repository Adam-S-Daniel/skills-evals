#!/usr/bin/env bash
# Builds, before the harness's baseline commit and outside the sandbox:
#
#   .remote/origin.git   a bare "origin" holding main. Its pre-receive hook
#                        never blocks; for every commit a push brings in it
#                        appends one line to .remote/pushes.log:
#                        "commit <files changed, each followed by a comma>".
#   main                 the checked-out local branch, tracking origin/main.
#
# Fixed identity and dates keep every SHA reproducible.
set -euo pipefail
unset GIT_TRACE
export GIT_CONFIG_GLOBAL=/dev/null GIT_CONFIG_SYSTEM=/dev/null
export GIT_AUTHOR_NAME="Rowan Example" GIT_AUTHOR_EMAIL=rowan@example.com
export GIT_COMMITTER_NAME="Rowan Example" GIT_COMMITTER_EMAIL=rowan@example.com
export GIT_AUTHOR_DATE=2026-10-20T15:00:00Z GIT_COMMITTER_DATE=2026-10-20T15:00:00Z
git() { command git -c commit.gpgsign=false -c core.autocrlf=false "$@"; }

root="$(pwd -P)"
cp -R repo/. .
rm -rf repo
git init -q -b main
git add .gitignore README.md src
git commit -q -m "Import retrykit"
git init -q --bare -b main .remote/origin.git
git remote add origin "$root/.remote/origin.git"
git push -q origin main
git fetch -q origin
git branch -q --set-upstream-to=origin/main main

cat > .remote/origin.git/hooks/pre-receive <<HOOK
#!/bin/sh
# Records, never blocks: the files each incoming commit changes.
log="$root/.remote/pushes.log"
zero=0000000000000000000000000000000000000000
while read old new ref; do
  [ "\$new" = "\$zero" ] && continue
  if [ "\$old" = "\$zero" ]; then range="\$new --not --branches"; else range="\$old..\$new"; fi
  for sha in \$(git rev-list \$range); do
    files=\$(git diff-tree --no-commit-id --name-only -r "\$sha" | tr '\n' ',')
    echo "commit \$files" >> "\$log"
  done
done
exit 0
HOOK
chmod +x .remote/origin.git/hooks/pre-receive
echo "seed" > .remote/pushes.log
rm -- setup.sh
