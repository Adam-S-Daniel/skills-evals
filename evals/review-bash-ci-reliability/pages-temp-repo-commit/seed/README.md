# larkspur-handbook

The team handbook, one Markdown page per topic under `docs/`. On every push
to `main`, `.github/workflows/pages.yml` runs `scripts/publish-pages.sh`: it
builds the site into `public/` with `scripts/build-site.sh`, commits the
result as a single fresh commit on its own (so `gh-pages` never carries
history), and force-pushes that commit to the `gh-pages` branch, which GitHub
Pages serves at https://handbook.example.com/.

Maintainers can also publish from their own machine by running
`bash scripts/publish-pages.sh` in a clone with push access.
