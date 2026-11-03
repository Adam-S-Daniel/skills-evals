# example-site
`test` in workflows/ci.yml is a required status check on main.
Recent PRs show `test` as cancelled even though no step failed; two runs start
for each head commit (opened, then labeled).
