"""Write an upcoming talk as a page in the site's _events collection."""
from __future__ import annotations

import re
from pathlib import Path


def slugify(text: str) -> str:
    """Lowercase ASCII words joined by hyphens, at most 60 characters."""
    words = re.findall(r"[a-z0-9]+", text.lower())
    return "-".join(words)[:60].strip("-") or "untitled"


def _q(value: str) -> str:
    """Double-quote a value for a front-matter line."""
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


def write_event(find: dict, out_dir: Path) -> Path:
    """Write one event find to out_dir/<start_date>-<slug>.md and return the path."""
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{find['start_date']}-{slugify(find['title'])}.md"
    lines = [
        "---",
        f"title: {_q(find['title'])}",
        f"venue: {_q(find['venue'])}",
        f"start_date: {_q(find['start_date'])}",
        f"url: {_q(find['url'])}",
        "---",
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")
    return path
