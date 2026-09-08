#!/bin/bash
HEADSHA=${1:?head sha required}
SP=/tmp/claude-0/-home-user-skills-evals/04a3a432-66e9-523a-9242-1a9645f26cfa/scratchpad
export PATH=$SP/bin:$PATH; echo "yq: $(which yq) $(yq --version 2>&1 | head -1)"
cd /home/user/_agent-guidance
git fetch origin "+refs/heads/claude/agent-guidance-123:refs/remotes/origin/claude/agent-guidance-123" "+refs/heads/main:refs/remotes/origin/main" 2>&1 | tail -1
echo "remote-head=$(git rev-parse origin/claude/agent-guidance-123) origin/main=$(git rev-parse origin/main)"
[ "$(git rev-parse origin/claude/agent-guidance-123)" = "$(git rev-parse $HEADSHA)" ] || { echo "REMOTE HEAD IS NOT $HEADSHA"; exit 1; }
W=$SP/ag-123-v4; rm -rf $W; git worktree prune; git worktree add --detach $W $HEADSHA >/dev/null 2>&1 || { echo "worktree add failed"; exit 1; }
cd $W; echo "HEAD=$(git rev-parse HEAD)"
fp() { find . -type f -not -path './node_modules/*' -not -path './.git/*' -print0 | sort -z | xargs -0 md5sum | md5sum; }
echo "fp-before=$(fp)"
if [ -f package.json ]; then (npm ci --ignore-scripts > $SP/124.npm4.log 2>&1; echo "npm-ci-exit=$?"); fi
H=$(mktemp -d); export HOME=$H; export CLAUDE_CONFIG_DIR=$H/.claude; env -u SP ./test/run-tests.sh > $SP/124.tests4.log 2>&1; echo "tests-exit=$?"; grep -E 'passed|failed' $SP/124.tests4.log | tail -3
bash scripts/check-agents-md.sh > $SP/124.gate-agents4.log 2>&1; echo "check-agents-md-exit=$?"
node scripts/check-guidance-coverage.js --check-bytes > $SP/124.gate-cov4.log 2>&1; echo "coverage-exit=$? $(tail -1 $SP/124.gate-cov4.log)"
node scripts/check-registry.js > $SP/124.gate-reg4.log 2>&1; echo "registry-exit=$?"
git status --porcelain | head -5
echo "github-diff vs 0d73ac4: [$(git diff --stat 0d73ac4..$HEADSHA -- .github/ | tail -1)]"
echo "files changed 0d73ac4..$HEADSHA:"; git diff --stat 0d73ac4..$HEADSHA | tail -15
echo "commits:"; git log --format='%h %ae %s' 0d73ac4..$HEADSHA | cat
echo "fp-after=$(fp)"
cd /home/user/_agent-guidance
echo "authors: $(git log --format='%ae %ce' 5f13def..$HEADSHA | sort -u | tr '\n' ';')"
git merge-base --is-ancestor 5f13def $HEADSHA && echo "5f13def (main) IS ancestor" || echo "main NOT ancestor"
git merge-tree --write-tree origin/main $HEADSHA >/dev/null 2>&1 && echo "merge-tree: clean" || echo "merge-tree: CONFLICT"
date -u
