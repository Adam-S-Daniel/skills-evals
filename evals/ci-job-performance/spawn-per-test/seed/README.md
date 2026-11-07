# sitelint

House-style checks for the example.com marketing pages: alt text, titles,
headings, links, inline styles and the words the style guide asks us to avoid.
This repository is private to the example-org web team.

```bash
python3 -m sitelint pages/*.html          # one line per finding
python3 -m sitelint --json pages/home.html
```

The tests use only the standard library:

```bash
python3 -m unittest discover -s tests
```

`lint-tests` in `.github/workflows/ci.yml` runs them on every pull request,
and branch protection requires that check on `main`.
