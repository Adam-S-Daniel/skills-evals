"""The house-style rules. Each rule reads a parsed page and yields findings."""

import re
from collections import namedtuple
from html.parser import HTMLParser

Finding = namedtuple("Finding", "path line rule message")

TITLE_MAX = 60
DESCRIPTION_MAX = 160

# Words the style guide asks writers to avoid in visible copy.
BANNED_PHRASES = (
    "best-in-class", "cutting-edge", "game-changing", "industry-leading",
    "leverage", "next-generation", "revolutionary", "seamless", "synergy",
    "world-class",
)
BANNED = re.compile(r"\b(?:" + "|".join(re.escape(p) for p in BANNED_PHRASES) + r")\b", re.I)


class Page(HTMLParser):
    """Everything the rules need, collected in one pass."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.html_lang = None
        self.saw_html = False
        self.title = None
        self.title_line = 1
        self.description = None
        self.images = []        # (line, attrs)
        self.links = []         # (line, attrs, text)
        self.headings = []      # (line, level)
        self.ids = []           # (line, id)
        self.styles = []        # line of each inline style attribute
        self.text = []          # (line, data) of visible text
        self._in_title = False
        self._link = None
        self._skip = 0

    def handle_starttag(self, tag, attrs):
        line = self.getpos()[0]
        attrs = dict(attrs)
        if "id" in attrs:
            self.ids.append((line, attrs["id"]))
        if "style" in attrs:
            self.styles.append(line)
        if tag == "html":
            self.saw_html = True
            self.html_lang = attrs.get("lang")
        elif tag == "title":
            self._in_title = True
            self.title = ""
            self.title_line = line
        elif tag == "meta" and (attrs.get("name") or "").lower() == "description":
            self.description = attrs.get("content") or ""
        elif tag == "img":
            self.images.append((line, attrs))
        elif tag == "a":
            self._link = [line, attrs, ""]
        elif re.fullmatch(r"h[1-6]", tag):
            self.headings.append((line, int(tag[1])))
        elif tag in ("script", "style"):
            self._skip += 1

    def handle_endtag(self, tag):
        if tag == "title":
            self._in_title = False
        elif tag == "a" and self._link is not None:
            self.links.append(tuple(self._link))
            self._link = None
        elif tag in ("script", "style") and self._skip:
            self._skip -= 1

    def handle_data(self, data):
        if self._in_title:
            self.title += data
        if self._link is not None:
            self._link[2] += data
        if not self._skip and not self._in_title and data.strip():
            self.text.append((self.getpos()[0], data))


def check_lang(page, path):
    if page.saw_html and not page.html_lang:
        yield Finding(path, 1, "missing-lang", "<html> has no lang attribute")


def check_title(page, path):
    if page.title is None or not page.title.strip():
        yield Finding(path, page.title_line, "missing-title", "page has no <title>")
    elif len(page.title.strip()) > TITLE_MAX:
        yield Finding(path, page.title_line, "long-title",
                      f"title is {len(page.title.strip())} characters (max {TITLE_MAX})")


def check_description(page, path):
    if page.description is None:
        yield Finding(path, 1, "missing-description", "no meta description")
    elif len(page.description) > DESCRIPTION_MAX:
        yield Finding(path, 1, "long-description",
                      f"meta description is {len(page.description)} characters (max {DESCRIPTION_MAX})")


def check_images(page, path):
    for line, attrs in page.images:
        if "alt" not in attrs:
            yield Finding(path, line, "missing-alt", "<img> has no alt attribute")


def check_links(page, path):
    for line, attrs, text in page.links:
        href = attrs.get("href") or ""
        if not text.strip() and not attrs.get("aria-label"):
            yield Finding(path, line, "empty-link", "link has no text")
        if href.startswith("http://"):
            yield Finding(path, line, "insecure-link", f"{href} is not https")


def check_headings(page, path):
    ones = [line for line, level in page.headings if level == 1]
    if len(ones) != 1:
        yield Finding(path, ones[1] if len(ones) > 1 else 1, "h1-count",
                      f"page has {len(ones)} <h1> elements (want 1)")
    previous = 0
    for line, level in page.headings:
        if previous and level > previous + 1:
            yield Finding(path, line, "heading-skip", f"<h{level}> follows <h{previous}>")
        previous = level


def check_ids(page, path):
    seen = set()
    for line, value in page.ids:
        if value in seen:
            yield Finding(path, line, "duplicate-id", f"id {value!r} is used more than once")
        seen.add(value)


def check_styles(page, path):
    for line in page.styles:
        yield Finding(path, line, "inline-style", "inline style attribute")


def check_copy(page, path):
    for line, data in page.text:
        for match in BANNED.finditer(data):
            yield Finding(path, line, "banned-phrase", f"avoid {match.group(0)!r}")


def check_whitespace(lines, path):
    for number, text in enumerate(lines, 1):
        if text != text.rstrip():
            yield Finding(path, number, "trailing-whitespace", "line ends in whitespace")


PAGE_RULES = (check_lang, check_title, check_description, check_images, check_links,
              check_headings, check_ids, check_styles, check_copy)


def lint_text(text, path="<page>"):
    """Every finding for one page's HTML, in line order."""
    page = Page()
    page.feed(text)
    page.close()
    findings = [f for rule in PAGE_RULES for f in rule(page, path)]
    findings.extend(check_whitespace(text.splitlines(), path))
    return sorted(findings, key=lambda f: (f.line, f.rule))


def lint_file(path):
    with open(path, encoding="utf-8") as handle:
        return lint_text(handle.read(), path)
