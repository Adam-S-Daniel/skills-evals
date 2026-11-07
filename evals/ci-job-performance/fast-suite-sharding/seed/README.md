# Example site

The public marketing site for example.com. The end-to-end tests live in
`e2e/` and run in Chromium on every push and pull request through the `e2e`
workflow. Branch protection on `main` requires the `e2e` status check.

Run them locally with:

```bash
cd e2e
npm ci
npx playwright install --with-deps chromium
npx playwright test
```
