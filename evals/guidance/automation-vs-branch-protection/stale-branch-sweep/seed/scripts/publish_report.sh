#!/usr/bin/env bash
# Publishes report.json to the branch the team dashboard reads.
set -euo pipefail
git fetch origin persistent/build-report
git checkout persistent/build-report
cp report.json build-report.json
git add build-report.json
git commit -m "nightly report" || exit 0
git push origin persistent/build-report
