"""Turn the scraper's finds into pages for the site.

Each find is a dict from the scraper. Its text fields (title, outlet,
summary) are copied verbatim from the page the scraper found, so they can
hold anything that page held.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from media_discovery import events, render

SITE_ROOT = Path(__file__).resolve().parents[2]


def main(argv: list[str]) -> int:
    finds = json.loads(Path(argv[1]).read_text(encoding="utf-8"))
    for find in finds:
        if find["kind"] == "event":
            path = events.write_event(find, SITE_ROOT / "_events")
        else:
            path = render.write_entry(find, SITE_ROOT / "_media")
        print(f"wrote {path.relative_to(SITE_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
