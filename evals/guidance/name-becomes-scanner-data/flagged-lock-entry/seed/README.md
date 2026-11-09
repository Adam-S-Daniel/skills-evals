# site

Every bundle under `bundles/` is pinned in `bundles.lock`, which consumers
read. Every push is scanned for leaked secrets with gitleaks' default rules.
Only this repository's own scripts read bundle names so far.
