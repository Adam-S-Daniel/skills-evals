# example-site

A Decap-CMS site built on `example-org/cms-platform`, pinned by
`platform.lock`. Editors publish through `/admin`; the editorial workflow
opens a `cms/<collection>/<slug>` pull request, and the publish loops in
`.github/workflows/` exercise that chain end to end against production.

Live at <https://www.example.com>. Preview deploys land under
`https://preview.example.net/<branch>/`.
