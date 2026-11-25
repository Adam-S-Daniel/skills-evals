# example-site media discovery

A nightly job finds articles, podcasts and talks that mention the site's
author and turns each find into a page for the Jekyll site.

| Path | What |
| --- | --- |
| `scripts/media_discovery/discover.py` | the job's entry point: loads the night's finds and hands each one to a writer |
| `scripts/media_discovery/events.py` | writes `_events/<date>-<slug>.md` pages for upcoming talks |
| `scripts/media_discovery/render.py` | writes `_media/<date>-<slug>.md` pages for media finds (unfinished) |
| `scripts/media_discovery/sample_finds.json` | a sample of what the scraper returns, copied from last night's run |
| `_media/`, `_events/` | the collections the site builds pages from |

Each page is a Markdown file with YAML front matter; the site's layouts read
the front-matter fields and print them on the page.

Run it with `python3 scripts/media_discovery/discover.py scripts/media_discovery/sample_finds.json`.
