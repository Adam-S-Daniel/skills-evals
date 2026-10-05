# Browser-testing fixture source

The seed vendors a read-only slice of
[`cms-platform` v0.1.130](https://github.com/Adam-S-Daniel/cms-platform/tree/v0.1.130)
at commit `381824060a448677eb78dc7cda5bf2889271d60f`. The copied files are
`playwright.config.js`, `e2e/base.js`, `e2e/spec-ast.js`,
`e2e/workflow-yaml-utils.js`, `e2e/site-capabilities.js`,
`e2e/base-collections-guards.js`, the three pure-file lint references
`e2e/base-collections-guard-registry.test.js`,
`e2e/status-dropdown-selector.test.js`, and `e2e/admin-tag-lint.test.js`, and
the example specs `e2e/cms-posts-list-runtime.spec.js`,
`e2e/cms-preview-url.spec.js`, and `e2e/cms-smoke.spec.js`. The examples are
complete upstream files and are excluded from new-spec scoring by basename.
`theme/admin/posts-list-enhance.js` is the upstream implementation of the
dashboard's `li` cards and preview-draft link. The seed has no draft-preview
solution spec.

Fixture-only substitutions replace the original sites' hostnames with
`example.com` and `example.net`, local HTTP example URLs with those reserved
domains, the source's GitHub API/example links with `example.net`, one function
name in a comment with an example-prefixed spelling, and two synthetic
test-token strings with `fixture-placeholder`. The complete source files are
retained with these fixture substitutions; the altered endpoints are never
called.
These files are read as source
by the objective verifier; none of the examples, full Playwright config, or
full platform lint tests are executed in scoring. The fixed `check-spec.js`
uses the vendored `spec-ast.js` parser and `acorn-walk` to analyze every new
spec without loading it. The complete upstream lints document the platform's
rules and are protected by `files_unchanged`; the fixture checks the relevant
facts in the new spec, then the judge examines whether the draft association
and preview destination are substantively correct. A real browser run is
outside this fixture's pure-filesystem evidence.
The fixture pins the verifier's digest, and that verifier checks the copied
`spec-ast.js` and installed Acorn parser entrypoints before importing them.

The objective checks recognize direct `test()` declarations and describe
tags, an early direct `test.skip(!cap.keepsBaseCollection(SITE_ROOT,
"posts"), ...)`, and relative or Playwright-fixture-`baseURL` navigation.
They do not resolve helper-driven or dynamic routing. The entry-navigation
check conservatively treats every `goto` in one test callback as the same
page; aliasing and separate page contexts are judge scope. The verifier does
not execute the complete upstream lint suites or a browser.

The exact dependency pins are `acorn@8.18.0` (2026-07-28),
`acorn-walk@8.3.5` (2026-02-19), and `yaml@2.9.1` (2026-09-11), with a
committed lockfile. `npm ci --ignore-scripts --no-audit --no-fund` provisions
them before the agent and the local suite. No Playwright browser is installed
or launched by this fixture.
