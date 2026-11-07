#!/usr/bin/env python3
"""Count the docs pages and their words, for the docs site's footer.

usage: scripts/gen_stats.py [OUTPUT]   (default: docs/stats.json)
"""
import json
import sys
from pathlib import Path

pages = sorted(p for p in Path("docs").glob("*.md"))
stats = {"pages": len(pages),
         "words": sum(len(p.read_text(encoding="utf-8").split()) for p in pages),
         "by_page": {p.name: len(p.read_text(encoding="utf-8").split()) for p in pages}}
out = Path(sys.argv[1] if len(sys.argv) > 1 else "docs/stats.json")
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(json.dumps(stats, indent=2, sort_keys=True) + "\n", encoding="utf-8")
print(f"wrote {out}: {stats['pages']} pages, {stats['words']} words")
