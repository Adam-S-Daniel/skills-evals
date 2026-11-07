"""What sitelint reports for each page under pages/.

Each test runs the sitelint command line on one page, the way CI and the
pre-publish hook run it, and checks the lines one rule reports.
"""

import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def lines(page, rule):
    """The line numbers `rule` reports on `page`, from the command line."""
    result = subprocess.run(
        [sys.executable, "-m", "sitelint", "--json", page],
        cwd=ROOT, capture_output=True, text=True, check=False)
    if result.returncode not in (0, 1):
        raise AssertionError(f"sitelint exited {result.returncode}: {result.stderr}")
    return sorted(f["line"] for f in json.loads(result.stdout) if f["rule"] == rule)


class AboutPageTests(unittest.TestCase):
    page = "pages/about.html"

    def test_missing_lang(self):
        self.assertEqual(lines(self.page, "missing-lang"), [1])

    def test_missing_title(self):
        self.assertEqual(lines(self.page, "missing-title"), [])

    def test_long_title(self):
        self.assertEqual(lines(self.page, "long-title"), [5])

    def test_missing_description(self):
        self.assertEqual(lines(self.page, "missing-description"), [1])

    def test_long_description(self):
        self.assertEqual(lines(self.page, "long-description"), [])

    def test_missing_alt(self):
        self.assertEqual(lines(self.page, "missing-alt"), [])

    def test_empty_link(self):
        self.assertEqual(lines(self.page, "empty-link"), [])

    def test_insecure_link(self):
        self.assertEqual(lines(self.page, "insecure-link"), [])

    def test_h1_count(self):
        self.assertEqual(lines(self.page, "h1-count"), [])

    def test_heading_skip(self):
        self.assertEqual(lines(self.page, "heading-skip"), [])

    def test_duplicate_id(self):
        self.assertEqual(lines(self.page, "duplicate-id"), [12])

    def test_inline_style(self):
        self.assertEqual(lines(self.page, "inline-style"), [])

    def test_banned_phrase(self):
        self.assertEqual(lines(self.page, "banned-phrase"), [])

    def test_trailing_whitespace(self):
        self.assertEqual(lines(self.page, "trailing-whitespace"), [])


class BlogPageTests(unittest.TestCase):
    page = "pages/blog.html"

    def test_missing_lang(self):
        self.assertEqual(lines(self.page, "missing-lang"), [])

    def test_missing_title(self):
        self.assertEqual(lines(self.page, "missing-title"), [])

    def test_long_title(self):
        self.assertEqual(lines(self.page, "long-title"), [])

    def test_missing_description(self):
        self.assertEqual(lines(self.page, "missing-description"), [])

    def test_long_description(self):
        self.assertEqual(lines(self.page, "long-description"), [1])

    def test_missing_alt(self):
        self.assertEqual(lines(self.page, "missing-alt"), [14, 15])

    def test_empty_link(self):
        self.assertEqual(lines(self.page, "empty-link"), [])

    def test_insecure_link(self):
        self.assertEqual(lines(self.page, "insecure-link"), [])

    def test_h1_count(self):
        self.assertEqual(lines(self.page, "h1-count"), [10])

    def test_heading_skip(self):
        self.assertEqual(lines(self.page, "heading-skip"), [])

    def test_duplicate_id(self):
        self.assertEqual(lines(self.page, "duplicate-id"), [])

    def test_inline_style(self):
        self.assertEqual(lines(self.page, "inline-style"), [])

    def test_banned_phrase(self):
        self.assertEqual(lines(self.page, "banned-phrase"), [11, 12])

    def test_trailing_whitespace(self):
        self.assertEqual(lines(self.page, "trailing-whitespace"), [])


class CareersPageTests(unittest.TestCase):
    page = "pages/careers.html"

    def test_missing_lang(self):
        self.assertEqual(lines(self.page, "missing-lang"), [])

    def test_missing_title(self):
        self.assertEqual(lines(self.page, "missing-title"), [])

    def test_long_title(self):
        self.assertEqual(lines(self.page, "long-title"), [])

    def test_missing_description(self):
        self.assertEqual(lines(self.page, "missing-description"), [])

    def test_long_description(self):
        self.assertEqual(lines(self.page, "long-description"), [])

    def test_missing_alt(self):
        self.assertEqual(lines(self.page, "missing-alt"), [])

    def test_empty_link(self):
        self.assertEqual(lines(self.page, "empty-link"), [])

    def test_insecure_link(self):
        self.assertEqual(lines(self.page, "insecure-link"), [13])

    def test_h1_count(self):
        self.assertEqual(lines(self.page, "h1-count"), [])

    def test_heading_skip(self):
        self.assertEqual(lines(self.page, "heading-skip"), [11])

    def test_duplicate_id(self):
        self.assertEqual(lines(self.page, "duplicate-id"), [14])

    def test_inline_style(self):
        self.assertEqual(lines(self.page, "inline-style"), [12])

    def test_banned_phrase(self):
        self.assertEqual(lines(self.page, "banned-phrase"), [])

    def test_trailing_whitespace(self):
        self.assertEqual(lines(self.page, "trailing-whitespace"), [])


class ContactPageTests(unittest.TestCase):
    page = "pages/contact.html"

    def test_missing_lang(self):
        self.assertEqual(lines(self.page, "missing-lang"), [])

    def test_missing_title(self):
        self.assertEqual(lines(self.page, "missing-title"), [])

    def test_long_title(self):
        self.assertEqual(lines(self.page, "long-title"), [])

    def test_missing_description(self):
        self.assertEqual(lines(self.page, "missing-description"), [])

    def test_long_description(self):
        self.assertEqual(lines(self.page, "long-description"), [])

    def test_missing_alt(self):
        self.assertEqual(lines(self.page, "missing-alt"), [])

    def test_empty_link(self):
        self.assertEqual(lines(self.page, "empty-link"), [])

    def test_insecure_link(self):
        self.assertEqual(lines(self.page, "insecure-link"), [])

    def test_h1_count(self):
        self.assertEqual(lines(self.page, "h1-count"), [])

    def test_heading_skip(self):
        self.assertEqual(lines(self.page, "heading-skip"), [])

    def test_duplicate_id(self):
        self.assertEqual(lines(self.page, "duplicate-id"), [])

    def test_inline_style(self):
        self.assertEqual(lines(self.page, "inline-style"), [10])

    def test_banned_phrase(self):
        self.assertEqual(lines(self.page, "banned-phrase"), [])

    def test_trailing_whitespace(self):
        self.assertEqual(lines(self.page, "trailing-whitespace"), [])


class DocsPageTests(unittest.TestCase):
    page = "pages/docs.html"

    def test_missing_lang(self):
        self.assertEqual(lines(self.page, "missing-lang"), [])

    def test_missing_title(self):
        self.assertEqual(lines(self.page, "missing-title"), [])

    def test_long_title(self):
        self.assertEqual(lines(self.page, "long-title"), [])

    def test_missing_description(self):
        self.assertEqual(lines(self.page, "missing-description"), [])

    def test_long_description(self):
        self.assertEqual(lines(self.page, "long-description"), [])

    def test_missing_alt(self):
        self.assertEqual(lines(self.page, "missing-alt"), [])

    def test_empty_link(self):
        self.assertEqual(lines(self.page, "empty-link"), [])

    def test_insecure_link(self):
        self.assertEqual(lines(self.page, "insecure-link"), [])

    def test_h1_count(self):
        self.assertEqual(lines(self.page, "h1-count"), [])

    def test_heading_skip(self):
        self.assertEqual(lines(self.page, "heading-skip"), [])

    def test_duplicate_id(self):
        self.assertEqual(lines(self.page, "duplicate-id"), [])

    def test_inline_style(self):
        self.assertEqual(lines(self.page, "inline-style"), [])

    def test_banned_phrase(self):
        self.assertEqual(lines(self.page, "banned-phrase"), [])

    def test_trailing_whitespace(self):
        self.assertEqual(lines(self.page, "trailing-whitespace"), [])


class FeaturesPageTests(unittest.TestCase):
    page = "pages/features.html"

    def test_missing_lang(self):
        self.assertEqual(lines(self.page, "missing-lang"), [])

    def test_missing_title(self):
        self.assertEqual(lines(self.page, "missing-title"), [])

    def test_long_title(self):
        self.assertEqual(lines(self.page, "long-title"), [])

    def test_missing_description(self):
        self.assertEqual(lines(self.page, "missing-description"), [])

    def test_long_description(self):
        self.assertEqual(lines(self.page, "long-description"), [])

    def test_missing_alt(self):
        self.assertEqual(lines(self.page, "missing-alt"), [17])

    def test_empty_link(self):
        self.assertEqual(lines(self.page, "empty-link"), [])

    def test_insecure_link(self):
        self.assertEqual(lines(self.page, "insecure-link"), [])

    def test_h1_count(self):
        self.assertEqual(lines(self.page, "h1-count"), [])

    def test_heading_skip(self):
        self.assertEqual(lines(self.page, "heading-skip"), [])

    def test_duplicate_id(self):
        self.assertEqual(lines(self.page, "duplicate-id"), [])

    def test_inline_style(self):
        self.assertEqual(lines(self.page, "inline-style"), [])

    def test_banned_phrase(self):
        self.assertEqual(lines(self.page, "banned-phrase"), [])

    def test_trailing_whitespace(self):
        self.assertEqual(lines(self.page, "trailing-whitespace"), [])


class HomePageTests(unittest.TestCase):
    page = "pages/home.html"

    def test_missing_lang(self):
        self.assertEqual(lines(self.page, "missing-lang"), [])

    def test_missing_title(self):
        self.assertEqual(lines(self.page, "missing-title"), [])

    def test_long_title(self):
        self.assertEqual(lines(self.page, "long-title"), [])

    def test_missing_description(self):
        self.assertEqual(lines(self.page, "missing-description"), [])

    def test_long_description(self):
        self.assertEqual(lines(self.page, "long-description"), [])

    def test_missing_alt(self):
        self.assertEqual(lines(self.page, "missing-alt"), [])

    def test_empty_link(self):
        self.assertEqual(lines(self.page, "empty-link"), [])

    def test_insecure_link(self):
        self.assertEqual(lines(self.page, "insecure-link"), [])

    def test_h1_count(self):
        self.assertEqual(lines(self.page, "h1-count"), [])

    def test_heading_skip(self):
        self.assertEqual(lines(self.page, "heading-skip"), [])

    def test_duplicate_id(self):
        self.assertEqual(lines(self.page, "duplicate-id"), [])

    def test_inline_style(self):
        self.assertEqual(lines(self.page, "inline-style"), [])

    def test_banned_phrase(self):
        self.assertEqual(lines(self.page, "banned-phrase"), [13])

    def test_trailing_whitespace(self):
        self.assertEqual(lines(self.page, "trailing-whitespace"), [])


class LegalPageTests(unittest.TestCase):
    page = "pages/legal.html"

    def test_missing_lang(self):
        self.assertEqual(lines(self.page, "missing-lang"), [])

    def test_missing_title(self):
        self.assertEqual(lines(self.page, "missing-title"), [1])

    def test_long_title(self):
        self.assertEqual(lines(self.page, "long-title"), [])

    def test_missing_description(self):
        self.assertEqual(lines(self.page, "missing-description"), [1])

    def test_long_description(self):
        self.assertEqual(lines(self.page, "long-description"), [])

    def test_missing_alt(self):
        self.assertEqual(lines(self.page, "missing-alt"), [])

    def test_empty_link(self):
        self.assertEqual(lines(self.page, "empty-link"), [11])

    def test_insecure_link(self):
        self.assertEqual(lines(self.page, "insecure-link"), [11])

    def test_h1_count(self):
        self.assertEqual(lines(self.page, "h1-count"), [1])

    def test_heading_skip(self):
        self.assertEqual(lines(self.page, "heading-skip"), [])

    def test_duplicate_id(self):
        self.assertEqual(lines(self.page, "duplicate-id"), [])

    def test_inline_style(self):
        self.assertEqual(lines(self.page, "inline-style"), [11])

    def test_banned_phrase(self):
        self.assertEqual(lines(self.page, "banned-phrase"), [])

    def test_trailing_whitespace(self):
        self.assertEqual(lines(self.page, "trailing-whitespace"), [8])


class PartnersPageTests(unittest.TestCase):
    page = "pages/partners.html"

    def test_missing_lang(self):
        self.assertEqual(lines(self.page, "missing-lang"), [])

    def test_missing_title(self):
        self.assertEqual(lines(self.page, "missing-title"), [])

    def test_long_title(self):
        self.assertEqual(lines(self.page, "long-title"), [])

    def test_missing_description(self):
        self.assertEqual(lines(self.page, "missing-description"), [1])

    def test_long_description(self):
        self.assertEqual(lines(self.page, "long-description"), [])

    def test_missing_alt(self):
        self.assertEqual(lines(self.page, "missing-alt"), [12])

    def test_empty_link(self):
        self.assertEqual(lines(self.page, "empty-link"), [12])

    def test_insecure_link(self):
        self.assertEqual(lines(self.page, "insecure-link"), [])

    def test_h1_count(self):
        self.assertEqual(lines(self.page, "h1-count"), [])

    def test_heading_skip(self):
        self.assertEqual(lines(self.page, "heading-skip"), [13])

    def test_duplicate_id(self):
        self.assertEqual(lines(self.page, "duplicate-id"), [])

    def test_inline_style(self):
        self.assertEqual(lines(self.page, "inline-style"), [11])

    def test_banned_phrase(self):
        self.assertEqual(lines(self.page, "banned-phrase"), [14])

    def test_trailing_whitespace(self):
        self.assertEqual(lines(self.page, "trailing-whitespace"), [9])


class PricingPageTests(unittest.TestCase):
    page = "pages/pricing.html"

    def test_missing_lang(self):
        self.assertEqual(lines(self.page, "missing-lang"), [])

    def test_missing_title(self):
        self.assertEqual(lines(self.page, "missing-title"), [])

    def test_long_title(self):
        self.assertEqual(lines(self.page, "long-title"), [])

    def test_missing_description(self):
        self.assertEqual(lines(self.page, "missing-description"), [])

    def test_long_description(self):
        self.assertEqual(lines(self.page, "long-description"), [])

    def test_missing_alt(self):
        self.assertEqual(lines(self.page, "missing-alt"), [14])

    def test_empty_link(self):
        self.assertEqual(lines(self.page, "empty-link"), [16])

    def test_insecure_link(self):
        self.assertEqual(lines(self.page, "insecure-link"), [15])

    def test_h1_count(self):
        self.assertEqual(lines(self.page, "h1-count"), [])

    def test_heading_skip(self):
        self.assertEqual(lines(self.page, "heading-skip"), [10])

    def test_duplicate_id(self):
        self.assertEqual(lines(self.page, "duplicate-id"), [])

    def test_inline_style(self):
        self.assertEqual(lines(self.page, "inline-style"), [])

    def test_banned_phrase(self):
        self.assertEqual(lines(self.page, "banned-phrase"), [13])

    def test_trailing_whitespace(self):
        self.assertEqual(lines(self.page, "trailing-whitespace"), [])


class SecurityPageTests(unittest.TestCase):
    page = "pages/security.html"

    def test_missing_lang(self):
        self.assertEqual(lines(self.page, "missing-lang"), [])

    def test_missing_title(self):
        self.assertEqual(lines(self.page, "missing-title"), [])

    def test_long_title(self):
        self.assertEqual(lines(self.page, "long-title"), [])

    def test_missing_description(self):
        self.assertEqual(lines(self.page, "missing-description"), [])

    def test_long_description(self):
        self.assertEqual(lines(self.page, "long-description"), [])

    def test_missing_alt(self):
        self.assertEqual(lines(self.page, "missing-alt"), [])

    def test_empty_link(self):
        self.assertEqual(lines(self.page, "empty-link"), [])

    def test_insecure_link(self):
        self.assertEqual(lines(self.page, "insecure-link"), [13])

    def test_h1_count(self):
        self.assertEqual(lines(self.page, "h1-count"), [])

    def test_heading_skip(self):
        self.assertEqual(lines(self.page, "heading-skip"), [])

    def test_duplicate_id(self):
        self.assertEqual(lines(self.page, "duplicate-id"), [])

    def test_inline_style(self):
        self.assertEqual(lines(self.page, "inline-style"), [])

    def test_banned_phrase(self):
        self.assertEqual(lines(self.page, "banned-phrase"), [10])

    def test_trailing_whitespace(self):
        self.assertEqual(lines(self.page, "trailing-whitespace"), [])


class StatusPageTests(unittest.TestCase):
    page = "pages/status.html"

    def test_missing_lang(self):
        self.assertEqual(lines(self.page, "missing-lang"), [])

    def test_missing_title(self):
        self.assertEqual(lines(self.page, "missing-title"), [])

    def test_long_title(self):
        self.assertEqual(lines(self.page, "long-title"), [])

    def test_missing_description(self):
        self.assertEqual(lines(self.page, "missing-description"), [])

    def test_long_description(self):
        self.assertEqual(lines(self.page, "long-description"), [])

    def test_missing_alt(self):
        self.assertEqual(lines(self.page, "missing-alt"), [])

    def test_empty_link(self):
        self.assertEqual(lines(self.page, "empty-link"), [])

    def test_insecure_link(self):
        self.assertEqual(lines(self.page, "insecure-link"), [])

    def test_h1_count(self):
        self.assertEqual(lines(self.page, "h1-count"), [])

    def test_heading_skip(self):
        self.assertEqual(lines(self.page, "heading-skip"), [])

    def test_duplicate_id(self):
        self.assertEqual(lines(self.page, "duplicate-id"), [])

    def test_inline_style(self):
        self.assertEqual(lines(self.page, "inline-style"), [])

    def test_banned_phrase(self):
        self.assertEqual(lines(self.page, "banned-phrase"), [])

    def test_trailing_whitespace(self):
        self.assertEqual(lines(self.page, "trailing-whitespace"), [])


if __name__ == "__main__":
    unittest.main()
