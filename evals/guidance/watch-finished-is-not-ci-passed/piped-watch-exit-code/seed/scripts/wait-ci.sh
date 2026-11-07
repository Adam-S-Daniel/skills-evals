#!/usr/bin/env bash
# Wait for a CI run to finish and say whether it passed.
# The watch output is long, so only its tail is kept, in .ci-watch.tail.
run=${1:?usage: scripts/wait-ci.sh <run-id>}
gh run watch "$run" --exit-status --interval 10 2>&1 | tail -n 4 > .ci-watch.tail
if [ $? -eq 0 ]; then
  echo "CI run $run: passed"
else
  echo "CI run $run: FAILED (see .ci-watch.tail)"
fi
