# AGENTS.md

Inventory service and its report scripts. Go code lives at the root and under
`internal/`; helper scripts live under `scripts/`.

## Code quality

| Language | Tool | Config |
| --- | --- | --- |
| JavaScript | ESLint, Prettier | `.prettierrc` |
| Python | Ruff | `ruff.toml` |
| Ruby | RuboCop (standalone) | `.rubocop.yml` |
| Markdown | markdownlint | `.markdownlint.json` |
| YAML | yamllint | `.yamllint.yml` |
| Shell | ShellCheck, shfmt | none |

Enable the pre-commit hook once per clone:
`git config --local core.hooksPath .githooks`.
