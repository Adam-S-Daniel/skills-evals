# Example site

The marketing site for example.com. The end-to-end tests live in `e2e/` and
run on every push and pull request through the `e2e` workflow, once per
browser (Chromium, Firefox and WebKit).

Run them locally with:

```bash
cd e2e
npm ci
npx playwright install --with-deps
npx playwright test
```
