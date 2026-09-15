#!/bin/bash
SP=/tmp/claude-0/-home-user-skills-evals/04a3a432-66e9-523a-9242-1a9645f26cfa/scratchpad
cd /home/user/skills-evals
W=$SP/se-80-v5; rm -rf $W; git worktree prune; git worktree add --detach $W 8b92114 >/dev/null 2>&1 || { echo "worktree add failed"; exit 1; }
cd $W; echo "HEAD=$(git rev-parse HEAD)"
fp() { find harness test evals .github scripts -type f -not -path '*/__pycache__/*' -print0 | sort -z | xargs -0 md5sum | md5sum; }
echo "fp-before=$(fp)"
env -u SP python3 test/run_tests.py > $SP/80.tests5.log 2>&1; echo "tests-exit=$?"; tail -3 $SP/80.tests5.log
python3 test/test_propagation.py > $SP/80.prop5.log 2>&1; echo "prop-exit=$?"; tail -3 $SP/80.prop5.log
for fx in existing-convention bootstrap; do python3 harness/run_eval.py evals/writing-adrs/$fx --arm objective-only > $SP/80.fx5.$fx.log 2>&1; echo "fixture $fx exit=$?"; grep -c 'FAIL\|fail' $SP/80.fx5.$fx.log; done
echo "== fixtures head vs mainx4 (d5e06ee)"; for f in $(find evals -name fixture.yaml -printf '%h\n' | sort); do h=$(python3 $SP/cmpfix.py $W $f 2>/dev/null); m=$(python3 $SP/cmpfix.py $SP/mainx4 $f 2>/dev/null); if [ "$h" = "$m" ]; then echo "SAME $f: $h"; else echo "DIFF $f"; echo "  head: $h"; echo "  main: $m"; fi; done
echo "fp-after=$(fp)"
cd /home/user/skills-evals
echo "github-diff vs main:"; git diff --stat origin/main..8b92114 -- .github/ | cat
echo "seed-diff vs 78894af: $(git diff --stat 78894af..8b92114 -- 'evals/writing-adrs/*/seed' | tail -1)"
echo "authors: $(git log --format='%ae %ce' d5e06ee..8b92114 | sort -u | tr '\n' ';')"
git merge-base --is-ancestor d5e06ee 8b92114 && echo "d5e06ee IS ancestor" || echo "d5e06ee NOT ancestor"
git merge-tree --write-tree origin/main 8b92114 >/dev/null 2>&1 && echo "merge-tree: clean" || echo "merge-tree: CONFLICT"
date -u
