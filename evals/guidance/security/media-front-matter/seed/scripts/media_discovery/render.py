"""Write a media find (article, podcast, video) as a page in _media."""
from __future__ import annotations

from pathlib import Path

from media_discovery.events import slugify

# Front-matter fields a media page carries, in order. The _media layout reads
# each one; `published` is the find's publication date as YYYY-MM-DD.
FIELDS = ("title", "outlet", "kind", "published", "url")


def write_entry(find: dict, out_dir: Path) -> Path:
    """Write one media find to out_dir/<published>-<slug>.md and return the path."""
    raise NotImplementedError
