# gadgets

Feature work happens on short-lived branches and lands through pull requests.
The nightly job in `.github/workflows/nightly-report.yml` publishes build
numbers to the branch `persistent/build-report`, which the team dashboard
reads. `.github/rulesets/` holds the repository's branch rulesets.
