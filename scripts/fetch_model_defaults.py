#!/usr/bin/env python3
"""Read which model VERSION each Claude Code alias resolves to by default.

The roster seats a tier's vendor-default model the day it changes (#202,
docs/decisions/0002-roster-follows-vendor-defaults.md), so it needs to know
what the default IS. The source is the Markdown build of the Claude Code
model-config docs: the "Anthropic API" row of its provider table (the
`opus` / `sonnet` columns) and the prose sentence on `fable` resolution.
What comes out are display names ("Opus 5.5"); `harness/roster.py` matches
them to ids through the Models API's `display_name`.

Why the docs and not `claude --model <alias>`: the CLI resolves aliases
itself, so a probe reports the defaults of whichever CLI version is
installed, and CI's is pinned (ADR 0002 has the measured numbers).

  --out   {"fetched_at", "source", "defaults": {alias: display name},
           "error": null | "<HTTP status or exception class>"}

A FAILURE IS NOT FATAL. A fetch or parse failure writes `defaults: {}` with
a short `error`, prints one `fetch_model_defaults: ` line, and exits 0; the
roster then falls back to its newest-in-tier rule for every tier and says
so. Only a usage error (bad arguments, an unwritable `--out`) exits
non-zero. What is printed or recorded is a status code or an exception
class name and nothing else — never a response body — the same discipline
as `scripts/refresh_models.py`, for the same reason: this runs in a public
CI log.

No credential is read or sent, and no model id appears in this file.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from markdown_it import MarkdownIt

DOCS_URL = "https://code.claude.com/docs/en/model-config.md"
USER_AGENT = "skills-evals-roster (+https://github.com/Adam-S-Daniel/skills-evals)"
#: The page is ~100 KB; anything past this is not the page.
MAX_BYTES = 2 * 1024 * 1024
#: The provider row whose defaults a direct Models-API bearer gets.
PROVIDER_HEADER = "Provider"
PROVIDER_ROW = "Anthropic API"
#: An alias is a lowercase word; `sonnet[1m]` and friends are not family
#: aliases and are skipped by this shape rather than by a list.
ALIAS_RE = re.compile(r"^[a-z][a-z0-9_-]{0,31}\Z")
#: Lexical only, on the text token that FOLLOWS an inline code span — the
#: code span itself is found in the parse tree.
PROSE_RE = re.compile(r"^\s+alias resolves to\s+([A-Z][A-Za-z]*\s+\d+(?:\.\d+)*)")


def _inline_text(inline) -> str:
    """The plain text of an inline token: text and code spans, links unwrapped."""
    parts = []
    for child in inline.children or []:
        if child.type in ("text", "code_inline"):
            parts.append(child.content)
        elif child.type in ("softbreak", "hardbreak"):
            parts.append(" ")
    return "".join(parts).strip()


def _header_alias(inline) -> str | None:
    """The alias a header cell names, when the cell is exactly one code span."""
    children = [c for c in inline.children or []
                if not (c.type == "text" and not c.content.strip())]
    if len(children) == 1 and children[0].type == "code_inline":
        alias = children[0].content.strip().lower()
        if ALIAS_RE.match(alias):
            return alias
    return None


def _tables(tokens) -> list[list[list]]:
    """Every table as rows of cell inline tokens, header row first."""
    tables: list[list[list]] = []
    rows: list[list] | None = None
    row: list | None = None
    for index, token in enumerate(tokens):
        if token.type == "table_open":
            rows = []
        elif token.type == "table_close" and rows is not None:
            tables.append(rows)
            rows = None
        elif token.type == "tr_open" and rows is not None:
            row = []
        elif token.type == "tr_close" and rows is not None and row is not None:
            rows.append(row)
            row = None
        elif token.type in ("th_open", "td_open") and row is not None:
            row.append(tokens[index + 1])
    return tables


def _from_tables(tokens) -> dict[str, str]:
    for rows in _tables(tokens):
        if not rows or len(rows[0]) < 2:
            continue
        header = rows[0]
        if _inline_text(header[0]) != PROVIDER_HEADER:
            continue
        aliases = [_header_alias(cell) for cell in header[1:]]
        if not any(aliases):
            continue
        for row in rows[1:]:
            if not row or _inline_text(row[0]) != PROVIDER_ROW:
                continue
            found = {}
            for alias, cell in zip(aliases, row[1:]):
                name = _inline_text(cell)
                if alias and name:
                    found[alias] = name
            if found:
                return found
    return {}


def _from_prose(tokens) -> dict[str, str]:
    found: dict[str, str] = {}
    for index, token in enumerate(tokens):
        if token.type != "inline" or index == 0 or tokens[index - 1].type != "paragraph_open":
            continue
        children = token.children or []
        for position, child in enumerate(children[:-1]):
            follower = children[position + 1]
            if child.type != "code_inline" or follower.type != "text":
                continue
            alias = child.content.strip().lower()
            match = PROSE_RE.match(follower.content)
            if match and ALIAS_RE.match(alias) and alias not in found:
                found[alias] = " ".join(match.group(1).split())
    return found


def parse_defaults(markdown: str) -> dict[str, str]:
    """{alias: display name} from the model-config page; `{}` if none found.

    Parsed with a real Markdown parser, never a line scan: the table's alias
    columns are read from its HEADER, so a column the docs add is picked up
    without an edit here. The table wins over the prose for an alias both
    name.
    """
    tokens = MarkdownIt("commonmark").enable("table").parse(markdown or "")
    result = _from_prose(tokens)
    result.update(_from_tables(tokens))
    return result


def _fetch(url: str) -> str:
    # A named agent, not urllib's default: the docs host answers
    # `Python-urllib/3.x` with HTTP 403 (measured 2026-09-27).
    request = urllib.request.Request(
        url, headers={"accept": "text/markdown, text/plain",
                      "user-agent": USER_AGENT}, method="GET")
    with urllib.request.urlopen(request, timeout=30) as response:
        body = response.read(MAX_BYTES + 1)
    if len(body) > MAX_BYTES:
        raise ValueError("page too large")
    return body.decode("utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True,
                        help="where to write the defaults document")
    parser.add_argument("--url", default=DOCS_URL,
                        help="the Markdown model-config page to read")
    parser.add_argument("--from-file", type=Path, default=None,
                        help="parse a local copy instead of fetching")
    args = parser.parse_args()

    source = str(args.from_file) if args.from_file else args.url
    defaults: dict[str, str] = {}
    error = None
    try:
        if args.from_file:
            text = args.from_file.read_text(encoding="utf-8")
        else:
            text = _fetch(args.url)
        defaults = parse_defaults(text)
        if not defaults:
            error = "no-defaults-found"
    except urllib.error.HTTPError as exc:
        error = f"HTTP {exc.code}"
    # OSError covers URLError and timeouts; ValueError the decode and the
    # size cap; RecursionError a pathologically nested page.
    except (OSError, ValueError, RecursionError) as exc:
        error = type(exc).__name__
    if error:
        print(f"fetch_model_defaults: no vendor defaults read ({error}); the "
              f"roster falls back to newest-in-tier for every tier",
              file=sys.stderr)

    document = {"fetched_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "source": source, "defaults": defaults, "error": error}
    try:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        with open(args.out, "w", encoding="utf-8") as f:
            json.dump(document, f, indent=2)
            f.write("\n")
    except OSError as exc:
        print(f"fetch_model_defaults: cannot write --out ({type(exc).__name__})",
              file=sys.stderr)
        return 1
    print(f"fetch_model_defaults: {len(defaults)} alias default(s) written to {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
