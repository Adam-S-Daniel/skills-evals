#!/bin/bash
SP=/tmp/claude-0/-home-user-skills-evals/04a3a432-66e9-523a-9242-1a9645f26cfa/scratchpad
cd /home/user/skills-evals
W=$SP/se-67-v10; rm -rf $W; git worktree prune; git worktree add --detach $W 1fa9d3a >/dev/null 2>&1 || { echo "worktree add failed"; exit 1; }
cd $W; echo "HEAD=$(git rev-parse HEAD)"; ls -d ../_agent-guidance ../agentskills
fp() { find harness test evals .github scripts -type f -not -path '*/__pycache__/*' -print0 | sort -z | xargs -0 md5sum | md5sum; }
echo "fp-before=$(fp)"; echo "usermem-before=$(md5sum /root/.claude/CLAUDE.md)"
env -u SP python3 test/run_tests.py > $SP/67.tests10.log 2>&1; echo "tests-exit=$?"; tail -3 $SP/97.tests2.log
python3 test/test_propagation.py > $SP/67.prop10.log 2>&1; echo "prop-exit=$?"; tail -3 $SP/97.prop2.log
echo "== fixtures head vs mainx4 (d5e06ee)"; for f in $(find evals -name fixture.yaml -printf '%h\n' | sort); do case $f in evals/guidance/*) continue;; esac; h=$(python3 $SP/cmpfix.py $W $f 2>/dev/null); m=$(python3 $SP/cmpfix.py $SP/mainx4 $f 2>/dev/null); if [ "$h" = "$m" ]; then echo "SAME $f: $h"; else echo "DIFF $f"; echo "  head: $h"; echo "  main: $m"; fi; done
echo "fp-after=$(fp)"; echo "usermem-after=$(md5sum /root/.claude/CLAUDE.md)"; git status --porcelain | head -5
cd /home/user/skills-evals
echo "github-diff vs main:"; git diff --stat origin/main..1fa9d3a -- .github/ | cat
echo "seed-diff vs e6587f8: $(git diff --stat e6587f8..1fa9d3a -- 'evals/*/seed' 'evals/*/*/seed' | tail -1)"
echo "authors: $(git log --format='%ae %ce' d5e06ee..1fa9d3a | sort -u | tr '\n' ';')"
git merge-base --is-ancestor d5e06ee 1fa9d3a && echo "d5e06ee IS ancestor" || echo "d5e06ee NOT ancestor"
git merge-tree --write-tree origin/main 1fa9d3a >/dev/null 2>&1 && echo "merge-tree: clean" || echo "merge-tree: CONFLICT"
date -u
