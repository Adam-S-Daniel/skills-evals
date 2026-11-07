# guidebook

A tiny example.com documentation site. `pages/*.md` are copied to `dist/` by
`scripts/build.sh`; `scripts/check-links.sh` fails on a broken link.

CI is `.github/workflows/ci.yml`: `check` and `build`. To try the workflow
before pushing, `scripts/local-ci.sh` runs both jobs locally with act
(`scripts/install-act.sh` installs it). `tools/` lists the act releases and
runner images available from our mirror, with dates and checksums.
