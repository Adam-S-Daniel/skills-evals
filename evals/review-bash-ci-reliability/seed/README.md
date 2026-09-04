# example-repo

A small release pipeline used only as an eval fixture. `.github/workflows/release.yml`
runs three shell scripts (`scripts/collect.sh`, `scripts/publish.sh`, `scripts/bump.sh`)
on push to `main`. None of these scripts are executed by the eval harness; they exist
to be read and edited.
