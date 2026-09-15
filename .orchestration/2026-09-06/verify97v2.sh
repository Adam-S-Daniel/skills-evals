#!/bin/bash
SP=/tmp/claude-0/-home-user-skills-evals/04a3a432-66e9-523a-9242-1a9645f26cfa/scratchpad
cd /home/user/skills-evals
W=$SP/se-97-v2; rm -rf $W; git worktree prune; git worktree add --detach $W c5ea933 >/dev/null 2>&1 || { echo "worktree add failed"; exit 1; }
cd $W; echo "HEAD=$(git rev-parse HEAD)"; ls -d ../_agent-guidance ../agentskills
fp() { find harness test evals .github scripts -type f -not -path '*/__pycache__/*' -print0 | sort -z | xargs -0 md5sum | md5sum; }
echo "fp-before=$(fp)"; echo "usermem-before=$(md5sum /root/.claude/CLAUDE.md)"
env -u SP python3 test/run_tests.py > $SP/97.tests2.log 2>&1; echo "tests-exit=$?"; tail -3 $SP/97.tests2.log
python3 test/test_propagation.py > $SP/97.prop2.log 2>&1; echo "prop-exit=$?"; tail -3 $SP/97.prop2.log
python3 harness/run_eval.py evals/guidance/_delivery --arm objective-only > $SP/97.fx2.delivery.log 2>&1; echo "guidance/_delivery objective-only exit=$?"; tail -2 $SP/97.fx2.delivery.log
echo "== fixtures head vs mainx4 (d5e06ee)"; for f in $(find evals -name fixture.yaml -printf '%h\n' | sort); do case $f in evals/guidance/*) continue;; esac; h=$(python3 $SP/cmpfix.py $W $f 2>/dev/null); m=$(python3 $SP/cmpfix.py $SP/mainx4 $f 2>/dev/null); if [ "$h" = "$m" ]; then echo "SAME $f: $h"; else echo "DIFF $f"; echo "  head: $h"; echo "  main: $m"; fi; done
echo "fp-after=$(fp)"; echo "usermem-after=$(md5sum /root/.claude/CLAUDE.md)"; git status --porcelain | head -5
cd /home/user/skills-evals
echo "github-diff vs main:"; git diff --stat origin/main..c5ea933 -- .github/ | cat
echo "seed-diff vs 34ab8fc: $(git diff --stat 34ab8fc..c5ea933 -- 'evals/*/seed' 'evals/*/*/seed' | tail -1)"
echo "authors: $(git log --format='%ae %ce' d5e06ee..c5ea933 | sort -u | tr '\n' ';')"
git merge-base --is-ancestor d5e06ee c5ea933 && echo "d5e06ee IS ancestor" || echo "d5e06ee NOT ancestor"
git merge-tree --write-tree origin/main c5ea933 >/dev/null 2>&1 && echo "merge-tree: clean" || echo "merge-tree: CONFLICT"
date -u
