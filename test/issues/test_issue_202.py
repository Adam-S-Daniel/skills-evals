#!/usr/bin/env python3
"""Issue #202 — a tier's VENDOR-DEFAULT model takes its seat at once, and
the version it superseded retires after a buffer of complete ISO weeks
under the exit bar.

Three pieces, each tested here: `scripts/fetch_model_defaults.py` (reads the
Claude Code model-config docs page for which version each alias resolves
to), `harness/roster.py`'s `defaults_doc`/`--defaults` (seats that default and
retires what it superseded), and `harness/timeweeks.py`'s complete-week
helper the buffer is counted with.

Hermetic, like the rest of the suite: the docs parser is exercised on
Markdown strings in this file, never a live fetch — `urlopen` is patched to
raise wherever a test reaches the script's fetch path by accident — and every
roster call runs on a frozen `now`.

Discovered and run by test/run_tests.py (see `build_suite`/`DISCOVERY_DIR`
there); also runnable on its own with `python3 test/issues/test_issue_202.py`,
which really runs it — the `unittest.main()` at the bottom is what makes
that true.
"""

from __future__ import annotations

import contextlib
import copy
import io
import json
import shutil
import sys
import tempfile
import unittest
import urllib.error
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock

import yaml

TEST_DIR = Path(__file__).resolve().parent.parent
REPO_ROOT = TEST_DIR.parent
HARNESS_DIR = REPO_ROOT / "harness"
SCRIPTS_DIR = REPO_ROOT / "scripts"
POLICY = REPO_ROOT / "evals" / "roster-policy.yml"
EVAL_WORKFLOW = REPO_ROOT / ".github" / "workflows" / "eval.yml"

sys.path.insert(0, str(HARNESS_DIR))
import roster  # noqa: E402
import timeweeks  # noqa: E402

sys.path.insert(0, str(SCRIPTS_DIR))
import fetch_model_defaults  # noqa: E402


# The live page's relevant excerpt as of 2026-09-27, cell padding trimmed.
# Two traps it carries on purpose: the `best` row's "[`fable` alias resolves
# to](...)" sits inside a LINK with no name after it, and the `sonnet[1m]`
# row's "`sonnet` already resolves to Sonnet 5" is not the alias sentence.
LIVE_EXCERPT = """\
### Model aliases

Use a model alias to select model settings without remembering exact version numbers:

| Model alias      | Behavior |
| ---------------- | -------- |
| **`default`**    | Special value that clears any model override and reverts to the [runtime default for your account](#default-model-setting). Not itself a model alias |
| **`best`**       | Uses the model the [`fable` alias resolves to](#fable-alias-resolution) where Fable is available to you, otherwise the same model as `opus` |
| **`fable`**      | Uses the [Fable model for your provider](#fable-alias-resolution) for your hardest and longest-running tasks |
| **`sonnet`**     | Uses the latest Sonnet model for daily coding tasks |
| **`opus`**       | Uses the latest Opus model for complex reasoning tasks |
| **`haiku`**      | Uses the fast and efficient Haiku model for simple tasks |
| **`sonnet[1m]`** | Uses Sonnet with a [1 million token context window](https://example.com/cw) for long sessions. No effect when `sonnet` already resolves to Sonnet 5 with its native 1M window |

The version that the `opus` and `sonnet` aliases resolve to depends on the provider:

| Provider                                             | `opus`   | `sonnet`   |
| :--------------------------------------------------- | :------- | :--------- |
| Anthropic API                                        | Opus 5.5 | Sonnet 5   |
| [Claude Platform on AWS](/docs/en/claude-platform-on-aws) | Opus 5.5 | Sonnet 4.6 |
| Amazon Bedrock, Google Cloud's Agent Platform        | Opus 5.5 | Sonnet 4.5 |
| Microsoft Foundry                                    | Opus 4.6 | Sonnet 4.5 |

<span id="fable-alias-resolution" />

Unless you set `ANTHROPIC_DEFAULT_FABLE_MODEL`, the `fable` alias resolves to Fable 5.1, except in [Claude apps gateway](/docs/en/claude-apps-gateway) sessions, where `fable` and `best` resolve to Fable 5. Before v2.1.257, `fable` resolved to Fable 5 on every provider.

Before v2.1.280, `opus` resolved to Opus 5 on the Anthropic API.
"""


def _no_network(*_args, **_kwargs):
    raise AssertionError("a hermetic test reached urllib.request.urlopen")


class TestParseDefaults(unittest.TestCase):
    """`parse_defaults` — a real Markdown parse, never a line scan."""

    def test_the_live_page_shape_gives_opus_sonnet_and_fable(self):
        self.assertEqual(fetch_model_defaults.parse_defaults(LIVE_EXCERPT),
                         {"opus": "Opus 5.5", "sonnet": "Sonnet 5",
                          "fable": "Fable 5.1"})

    def test_a_table_alone_is_enough(self):
        text = ("| Provider | `opus` | `sonnet` |\n| --- | --- | --- |\n"
                "| Anthropic API | Opus 6 | Sonnet 6.1 |\n")
        self.assertEqual(fetch_model_defaults.parse_defaults(text),
                         {"opus": "Opus 6", "sonnet": "Sonnet 6.1"})

    def test_prose_alone_is_enough(self):
        text = "Plainly, the `fable` alias resolves to Fable 6, everywhere.\n"
        self.assertEqual(fetch_model_defaults.parse_defaults(text),
                         {"fable": "Fable 6"})

    def test_the_table_beats_the_prose_for_the_same_alias(self):
        text = ("The `opus` alias resolves to Opus 4 on old versions.\n\n"
                "| Provider | `opus` |\n| --- | --- |\n"
                "| Anthropic API | Opus 5.5 |\n")
        self.assertEqual(fetch_model_defaults.parse_defaults(text),
                         {"opus": "Opus 5.5"})

    def test_a_row_for_another_provider_is_ignored(self):
        text = ("| Provider | `opus` |\n| --- | --- |\n"
                "| Microsoft Foundry | Opus 4.6 |\n"
                "| Anthropic API (legacy) | Opus 4 |\n")
        self.assertEqual(fetch_model_defaults.parse_defaults(text), {})

    def test_alias_columns_come_from_the_header_not_a_hardcoded_list(self):
        text = ("| Provider | `haiku` | `opus` |\n| --- | --- | --- |\n"
                "| Anthropic API | Haiku 5 | Opus 5.5 |\n")
        self.assertEqual(fetch_model_defaults.parse_defaults(text),
                         {"haiku": "Haiku 5", "opus": "Opus 5.5"})

    def test_a_table_whose_first_header_is_not_provider_is_ignored(self):
        text = ("| Vendor | `opus` |\n| --- | --- |\n"
                "| Anthropic API | Opus 5.5 |\n")
        self.assertEqual(fetch_model_defaults.parse_defaults(text), {})

    def test_garbage_gives_an_empty_mapping(self):
        for text in ("", "not markdown at all {]", "<html><body>503</body></html>",
                     "| a | b |\n| - | - |\n| c | d |\n"):
            with self.subTest(text=text[:20]):
                self.assertEqual(fetch_model_defaults.parse_defaults(text), {})


class TestFetchScript(unittest.TestCase):
    """The CLI: writes the documented JSON, and a failure is not fatal."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)

    def _main(self, *argv):
        err = io.StringIO()
        with mock.patch.object(sys, "argv", ["fetch_model_defaults.py", *argv]), \
             mock.patch("urllib.request.urlopen", _no_network), \
             contextlib.redirect_stderr(err), \
             contextlib.redirect_stdout(io.StringIO()):
            rc = fetch_model_defaults.main()
        return rc, err.getvalue()

    def test_from_file_writes_the_documented_json(self):
        page = self.tmp / "mc.md"
        page.write_text(LIVE_EXCERPT, encoding="utf-8")
        out = self.tmp / "defaults.json"
        rc, _ = self._main("--from-file", str(page), "--out", str(out))
        self.assertEqual(rc, 0)
        doc = json.loads(out.read_text(encoding="utf-8"))
        self.assertEqual(sorted(doc), ["defaults", "error", "fetched_at", "source"])
        self.assertEqual(doc["defaults"], {"opus": "Opus 5.5", "sonnet": "Sonnet 5",
                                           "fable": "Fable 5.1"})
        self.assertIsNone(doc["error"])
        self.assertEqual(doc["source"], str(page))
        self.assertIsNotNone(timeweeks.parse_ts(doc["fetched_at"]))

    def test_a_missing_file_is_not_fatal(self):
        out = self.tmp / "defaults.json"
        rc, err = self._main("--from-file", str(self.tmp / "absent.md"),
                             "--out", str(out))
        self.assertEqual(rc, 0)
        doc = json.loads(out.read_text(encoding="utf-8"))
        self.assertEqual(doc["defaults"], {})
        self.assertEqual(doc["error"], "FileNotFoundError")
        self.assertIn("fetch_model_defaults: ", err)

    def test_a_page_with_nothing_in_it_records_no_defaults_found(self):
        page = self.tmp / "mc.md"
        page.write_text("# Nothing here\n", encoding="utf-8")
        out = self.tmp / "defaults.json"
        rc, _ = self._main("--from-file", str(page), "--out", str(out))
        self.assertEqual(rc, 0)
        doc = json.loads(out.read_text(encoding="utf-8"))
        self.assertEqual(doc, {**doc, "defaults": {}, "error": "no-defaults-found"})

    def test_an_http_error_records_the_status_only_and_is_not_fatal(self):
        def refuse(request, timeout=None):
            raise urllib.error.HTTPError(request.full_url, 503, "secret body text",
                                         {}, io.BytesIO(b"secret body text"))
        out = self.tmp / "defaults.json"
        err = io.StringIO()
        with mock.patch.object(sys, "argv", ["x", "--out", str(out)]), \
             mock.patch("urllib.request.urlopen", refuse), \
             contextlib.redirect_stderr(err), \
             contextlib.redirect_stdout(io.StringIO()):
            rc = fetch_model_defaults.main()
        self.assertEqual(rc, 0)
        doc = json.loads(out.read_text(encoding="utf-8"))
        self.assertEqual((doc["defaults"], doc["error"]), ({}, "HTTP 503"))
        self.assertEqual(doc["source"], fetch_model_defaults.DOCS_URL)
        self.assertNotIn("secret", err.getvalue() + out.read_text(encoding="utf-8"))

    def test_a_fetched_page_is_parsed(self):
        class Response(io.BytesIO):
            def __enter__(self):
                return self

            def __exit__(self, *exc):
                return False
        seen = []

        def serve(request, timeout=None):
            seen.append(request.full_url)
            return Response(LIVE_EXCERPT.encode("utf-8"))
        out = self.tmp / "defaults.json"
        with mock.patch.object(sys, "argv", ["x", "--url", "https://example.com/mc.md",
                                             "--out", str(out)]), \
             mock.patch("urllib.request.urlopen", serve), \
             contextlib.redirect_stdout(io.StringIO()):
            rc = fetch_model_defaults.main()
        self.assertEqual(rc, 0)
        self.assertEqual(seen, ["https://example.com/mc.md"])
        doc = json.loads(out.read_text(encoding="utf-8"))
        self.assertEqual(doc["defaults"]["opus"], "Opus 5.5")
        self.assertEqual(doc["source"], "https://example.com/mc.md")

    def test_the_request_names_its_own_user_agent(self):
        # The docs host answers urllib's default `Python-urllib/3.x` agent with
        # HTTP 403 and a named one with 200 (measured 2026-09-27), so without
        # this header every CI run silently degrades to newest-in-tier.
        seen = []

        def capture(request, timeout=None):
            seen.append(request.get_header("User-agent") or "")
            raise OSError("stop after capturing the request")
        out = self.tmp / "defaults.json"
        with mock.patch.object(sys, "argv", ["x", "--out", str(out)]), \
             mock.patch("urllib.request.urlopen", capture), \
             contextlib.redirect_stdout(io.StringIO()), \
             contextlib.redirect_stderr(io.StringIO()):
            fetch_model_defaults.main()
        self.assertEqual(len(seen), 1)
        self.assertTrue(seen[0].startswith("skills-evals-roster"), seen[0])

    def test_the_default_url_is_the_markdown_model_config_page(self):
        self.assertEqual(fetch_model_defaults.DOCS_URL,
                         "https://code.claude.com/docs/en/model-config.md")

    def test_an_unwritable_out_is_a_usage_error(self):
        page = self.tmp / "mc.md"
        page.write_text(LIVE_EXCERPT, encoding="utf-8")
        blocker = self.tmp / "file"
        blocker.write_text("", encoding="utf-8")
        rc, _ = self._main("--from-file", str(page),
                           "--out", str(blocker / "defaults.json"))
        self.assertNotEqual(rc, 0)


class TestCompleteWeeks(unittest.TestCase):
    """`timeweeks.complete_weeks_since` — the buffer's week count."""

    def test_a_week_counts_once_it_has_ended_and_began_after_the_start(self):
        count, labels = timeweeks.complete_weeks_since(
            datetime(2026, 9, 26, 12, tzinfo=timezone.utc),
            datetime(2026, 10, 6, 6, tzinfo=timezone.utc), 3)
        self.assertEqual((count, labels), (1, ["2026-W40"]))

    def test_the_boundaries_are_inclusive(self):
        # Starts exactly on W40's Monday midnight; ends exactly on W41's.
        count, labels = timeweeks.complete_weeks_since(
            datetime(2026, 9, 28, tzinfo=timezone.utc),
            datetime(2026, 10, 5, tzinfo=timezone.utc), 1)
        self.assertEqual((count, labels), (1, ["2026-W40"]))

    def test_nothing_complete_yet(self):
        self.assertEqual(timeweeks.complete_weeks_since(
            datetime(2026, 9, 26, 12, tzinfo=timezone.utc),
            datetime(2026, 10, 4, 23, tzinfo=timezone.utc), 1), (0, []))
        # An end before the start is not a negative count.
        self.assertEqual(timeweeks.complete_weeks_since(
            datetime(2026, 9, 26, tzinfo=timezone.utc),
            datetime(2026, 9, 1, tzinfo=timezone.utc), 1), (0, []))

    def test_only_the_most_recent_labels_are_returned(self):
        count, labels = timeweeks.complete_weeks_since(
            datetime(2026, 9, 1, tzinfo=timezone.utc),
            datetime(2026, 10, 6, tzinfo=timezone.utc), 2)
        self.assertEqual(count, 4)  # W37, W38, W39, W40
        self.assertEqual(labels, ["2026-W39", "2026-W40"])
        self.assertEqual(timeweeks.complete_weeks_since(
            datetime(2026, 9, 1, tzinfo=timezone.utc),
            datetime(2026, 10, 6, tzinfo=timezone.utc), 0), (4, []))


class _RosterFixture(unittest.TestCase):
    """Synthetic catalogue and census shaped like the 2026-09-22 census."""

    #: Sunday of 2026-W39. opus-5-5 shipped a day earlier.
    NOW = datetime(2026, 9, 27, 12, 0, 0, tzinfo=timezone.utc)
    #: Tuesday of 2026-W41: W40 (Sep 28 - Oct 4) is complete by then.
    LATER = datetime(2026, 10, 6, 12, 0, 0, tzinfo=timezone.utc)
    ENTER = ["2026-W36", "2026-W37", "2026-W38", "2026-W39"]

    @staticmethod
    def _model(model_id, display_name, created):
        return {"id": model_id, "display_name": display_name, "created_at": created}

    @classmethod
    def _models_doc(cls, extra=(), drop=()):
        models = [
            cls._model("claude-haiku-4-5", "Claude Haiku 4.5", "2025-10-01T00:00:00Z"),
            cls._model("claude-sonnet-4-6", "Claude Sonnet 4.6", "2025-11-24T00:00:00Z"),
            cls._model("claude-sonnet-5", "Claude Sonnet 5", "2026-02-01T00:00:00Z"),
            cls._model("claude-opus-4-8", "Claude Opus 4.8", "2026-01-15T00:00:00Z"),
            cls._model("claude-opus-5", "Claude Opus 5", "2026-04-01T00:00:00Z"),
            cls._model("claude-opus-5-5", "Claude Opus 5.5", "2026-09-26T12:00:00Z"),
            cls._model("claude-fable-5", "Claude Fable 5", "2026-05-01T00:00:00Z"),
            cls._model("claude-fable-5-1", "Claude Fable 5.1", "2026-09-01T00:00:00Z"),
        ]
        models = [m for m in models if m["id"] not in drop] + list(extra)
        return {"fetched_at": "2026-09-27T11:00:00Z", "models": models}

    @classmethod
    def _census(cls, generated_at="2026-09-22T06:00:00Z", extra=None):
        # 454 + 452 + 63 + 30 = 999 a week: 45.4%, 45.2%, 6.3%, 3.0%.
        counts = {
            "claude-sonnet-5": {w: 454 for w in cls.ENTER},
            "claude-opus-5": {w: 452 for w in cls.ENTER},
            "claude-haiku-4-5": {w: 63 for w in cls.ENTER},
            "claude-fable-5-1": {w: 30 for w in cls.ENTER},
        }
        for model_id, by_week in (extra or {}).items():
            counts.setdefault(model_id, {}).update(by_week)
        return {"generated_at": generated_at, "weeks": [], "counts": counts}

    @classmethod
    def _later_census(cls, opus5_w40, *, opus55_w40=0, generated_at="2026-10-06T06:00:00Z"):
        """The census a week on: W40 complete, opus-5 at `opus5_w40` turns."""
        w40 = {"claude-sonnet-5": 500, "claude-opus-5": opus5_w40,
               "claude-opus-5-5": opus55_w40, "claude-haiku-4-5": 60}
        return cls._census(generated_at=generated_at,
                           extra={m: {"2026-W40": n} for m, n in w40.items()})

    PREVIOUS = {"schema": 1,
                "arms": [{"id": "claude-sonnet-5"}, {"id": "claude-opus-5"}],
                "judge": {"id": "claude-fable-5-1", "is_arm": False},
                "preflight": {"id": "claude-haiku-4-5"},
                "catalogue_seen": []}

    DEFAULTS = {"fetched_at": "2026-09-27T10:00:00Z",
                "source": "https://code.claude.com/docs/en/model-config.md",
                "defaults": {"opus": "Opus 5.5", "sonnet": "Sonnet 5"},
                "error": None}

    @staticmethod
    def _policy(**overrides):
        policy = roster.load_policy(POLICY)
        policy.update(overrides)
        return policy

    def _compute(self, *, defaults=None, census=None, now=None, previous="default",
                 models=None, policy=None):
        warnings: list[str] = []
        result = roster.compute_roster(
            models_doc=models or self._models_doc(),
            census_doc=self._census() if census is None else census,
            policy=policy or self._policy(),
            previous=copy.deepcopy(self.PREVIOUS if previous == "default" else previous),
            now=now or self.NOW, warn=warnings.append,
            defaults_doc=defaults)
        return result, warnings

    @staticmethod
    def _arms(result):
        return [a["id"] for a in result["arms"]]

    @staticmethod
    def _reason(result, model_id, section="arms"):
        return next(e["reason"] for e in result[section] if e["id"] == model_id)


class TestVendorDefaultSeats(_RosterFixture):

    def test_the_202_worked_example(self):
        result, _ = self._compute(defaults=self.DEFAULTS)
        self.assertEqual(sorted(self._arms(result)),
                         ["claude-opus-5", "claude-opus-5-5", "claude-sonnet-5"])
        new = self._reason(result, "claude-opus-5-5")
        self.assertIn("vendor default for the opus tier", new)
        self.assertIn(self.DEFAULTS["source"], new)
        self.assertIn("2026-09-27T10:00:00Z", new)
        self.assertIn("`claude-opus-5` carries 45.2%", new)
        self.assertIn("no cooling-off", new)
        self.assertNotIn("past the", new)
        held = self._reason(result, "claude-opus-5")
        self.assertIn("superseded by `claude-opus-5-5`", held)
        self.assertIn("0 of 1", held)
        self.assertIn("vendor default for the sonnet tier",
                      self._reason(result, "claude-sonnet-5"))
        self.assertEqual(result["judge"]["id"], "claude-fable-5-1")
        self.assertEqual(result["defaults"]["resolved"],
                         {"opus": "claude-opus-5-5", "sonnet": "claude-sonnet-5"})
        self.assertEqual(result["defaults"]["unresolved"], [])
        self.assertEqual(result["defaults"]["source"], self.DEFAULTS["source"])
        self.assertEqual(result["proposal"]["status"], "differs")
        seat = next(c for c in result["proposal"]["changes"]
                    if c["to"] == "claude-opus-5-5")
        self.assertIn("vendor default", seat["reason"])

    def test_one_complete_week_under_the_exit_bar_retires_it(self):
        result, _ = self._compute(defaults=self.DEFAULTS, now=self.LATER,
                                  census=self._later_census(opus5_w40=5))
        self.assertNotIn("claude-opus-5", self._arms(result))
        self.assertIn("claude-opus-5-5", self._arms(result))
        why = self._reason(result, "claude-opus-5", "retired_since_last")
        self.assertIn("superseded by `claude-opus-5-5`", why)
        self.assertIn("2026-W40", why)
        self.assertIn("under the 2% exit bar", why)
        change = next(c for c in result["proposal"]["changes"]
                      if c["from"] == "claude-opus-5")
        self.assertIn("superseded", change["reason"])

    def test_one_complete_week_at_or_above_the_exit_bar_holds_it(self):
        result, _ = self._compute(defaults=self.DEFAULTS, now=self.LATER,
                                  census=self._later_census(opus5_w40=300))
        self.assertIn("claude-opus-5", self._arms(result))
        held = self._reason(result, "claude-opus-5")
        self.assertIn("superseded by `claude-opus-5-5`", held)
        self.assertIn("at or above the 2% exit bar", held)

    def test_a_stale_census_holds_it(self):
        census = self._later_census(opus5_w40=5)
        # Past the 14-day freshness window at LATER + 20 days.
        result, _ = self._compute(defaults=self.DEFAULTS, census=census,
                                  now=datetime(2026, 10, 26, 12, tzinfo=timezone.utc))
        self.assertIn("claude-opus-5", self._arms(result))
        held = self._reason(result, "claude-opus-5")
        self.assertIn("no evidence to retire it", held)
        self.assertIn("claude-opus-5-5", self._arms(result))

    def test_a_too_thin_buffer_window_holds_it(self):
        census = self._census(generated_at="2026-10-06T06:00:00Z",
                              extra={"claude-opus-5": {"2026-W40": 1},
                                     "claude-sonnet-5": {"2026-W40": 5}})
        result, _ = self._compute(defaults=self.DEFAULTS, census=census, now=self.LATER)
        self.assertIn("claude-opus-5", self._arms(result))
        self.assertIn("turn floor", self._reason(result, "claude-opus-5"))

    def test_zero_buffer_weeks_retires_it_at_once(self):
        result, _ = self._compute(defaults=self.DEFAULTS,
                                  policy=self._policy(superseded_exit_weeks=0))
        self.assertEqual(sorted(self._arms(result)),
                         ["claude-opus-5-5", "claude-sonnet-5"])
        why = self._reason(result, "claude-opus-5", "retired_since_last")
        self.assertIn("superseded by `claude-opus-5-5`", why)

    def test_a_superseded_model_gets_no_usage_seat(self):
        # opus-5 carries 45.2% but is not a previous arm: its usage keeps the
        # opus tier on the roster and seats the default, never itself.
        previous = {**self.PREVIOUS, "arms": [{"id": "claude-sonnet-5"}]}
        result, _ = self._compute(defaults=self.DEFAULTS, previous=previous)
        self.assertEqual(sorted(self._arms(result)),
                         ["claude-opus-5-5", "claude-sonnet-5"])
        why = self._reason(result, "claude-opus-5", "excluded")
        self.assertIn("superseded", why)
        # And out of its buffer, at 45% in the buffer week, a previous arm
        # is HELD by rule 3 (over the exit bar), not seated by usage.
        result, _ = self._compute(defaults=self.DEFAULTS, now=self.LATER,
                                  census=self._later_census(opus5_w40=450))
        held = self._reason(result, "claude-opus-5")
        self.assertNotIn("entry bar", held)
        self.assertIn("superseded", held)

    def test_a_preview_newer_than_the_default_takes_no_seat(self):
        defaults = {**self.DEFAULTS, "defaults": {"opus": "Opus 5", "sonnet": "Sonnet 5"}}
        # opus-5-5 is well past the cooling-off here, so today's rule would
        # seat it as newest in a qualifying tier.
        result, _ = self._compute(defaults=defaults, now=datetime(
            2026, 10, 8, 12, tzinfo=timezone.utc), census=self._later_census(
                opus5_w40=450, opus55_w40=40))
        self.assertNotIn("claude-opus-5-5", self._arms(result))
        self.assertIn("claude-opus-5", self._arms(result))
        why = self._reason(result, "claude-opus-5-5", "excluded")
        self.assertIn("newer than the vendor default `claude-opus-5`", why)

    def test_a_default_in_a_tier_that_is_not_on_the_roster_takes_no_seat(self):
        defaults = {**self.DEFAULTS, "defaults": {"opus": "Opus 5.5",
                                                  "sonnet": "Sonnet 5",
                                                  "fable": "Fable 5.1"}}
        result, _ = self._compute(defaults=defaults)
        self.assertNotIn("claude-fable-5-1", self._arms(result))
        self.assertEqual(result["defaults"]["resolved"]["fable"], "claude-fable-5-1")
        why = self._reason(result, "claude-fable-5-1", "excluded")
        self.assertIn("vendor default for the fable/mythos tier", why)
        self.assertIn("not on the roster", why)

    def test_a_previous_arm_puts_the_tier_on_the_roster(self):
        # Haiku carries 6.3% — under the entry bar — but a previous haiku arm
        # keeps the tier on the roster, so a new haiku default is seated.
        models = self._models_doc(extra=[self._model(
            "claude-haiku-5", "Claude Haiku 5", "2026-09-25T00:00:00Z")])
        previous = {**self.PREVIOUS, "arms": self.PREVIOUS["arms"]
                    + [{"id": "claude-haiku-4-5"}]}
        defaults = {**self.DEFAULTS, "defaults": {**self.DEFAULTS["defaults"],
                                                  "haiku": "Haiku 5"}}
        result, _ = self._compute(defaults=defaults, previous=previous, models=models)
        self.assertIn("claude-haiku-5", self._arms(result))
        self.assertIn("previous arm `claude-haiku-4-5`",
                      self._reason(result, "claude-haiku-5"))

    def test_with_no_usable_census_every_tier_is_on_the_roster(self):
        result, _ = self._compute(defaults=self.DEFAULTS, previous=None,
                                  census={"generated_at": None, "counts": {}})
        self.assertIn("claude-opus-5-5", self._arms(result))
        self.assertNotIn("claude-opus-5", self._arms(result))
        self.assertIn("no fresh census", self._reason(result, "claude-opus-5-5"))

    def test_the_summary_names_the_defaults_it_read(self):
        result, _ = self._compute(defaults=self.DEFAULTS)
        summary = roster.render_summary(result)
        self.assertIn("model defaults", summary)
        self.assertIn("2026-09-27T10:00:00Z", summary)


class TestUnresolvedDefaultsFallBack(_RosterFixture):
    """Every way a default can fail to resolve leaves its tier on today's
    rule — the cooling-off included — and says so in a warning."""

    def _assert_todays_opus_rule(self, result):
        # opus-5 by usage; opus-5-5 a day old, so the cooling-off excludes it.
        self.assertIn("claude-opus-5", self._arms(result))
        self.assertNotIn("claude-opus-5-5", self._arms(result))
        self.assertIn("cooling-off", self._reason(result, "claude-opus-5-5", "excluded"))
        self.assertNotIn("opus", result["defaults"]["resolved"])

    def test_an_unmatched_display_name(self):
        defaults = {**self.DEFAULTS, "defaults": {"opus": "Opus 9"}}
        result, warnings = self._compute(defaults=defaults)
        self._assert_todays_opus_rule(result)
        self.assertTrue(any("`opus`" in w and "no available model" in w
                            for w in warnings), warnings)
        self.assertEqual(result["defaults"]["unresolved"][0]["alias"], "opus")

    def test_an_ambiguous_display_name(self):
        models = self._models_doc(extra=[self._model(
            "claude-opus-5-5-fast", "Claude Opus 5.5", "2026-09-26T12:00:00Z")])
        result, warnings = self._compute(defaults={**self.DEFAULTS,
                                                   "defaults": {"opus": "Opus 5.5"}},
                                         models=models)
        self.assertNotIn("claude-opus-5-5", self._arms(result))
        self.assertNotIn("opus", result["defaults"]["resolved"])
        self.assertTrue(any("`opus`" in w and "2 available models" in w
                            for w in warnings), warnings)

    def test_a_display_name_in_the_wrong_tier(self):
        defaults = {**self.DEFAULTS, "defaults": {"opus": "Sonnet 5"}}
        result, warnings = self._compute(defaults=defaults)
        self._assert_todays_opus_rule(result)
        self.assertTrue(any("`opus`" in w and "sonnet tier" in w for w in warnings),
                        warnings)

    def test_an_alias_off_the_ladder_is_ignored(self):
        defaults = {**self.DEFAULTS, "defaults": {"opusplan": "Opus 5.5"}}
        result, warnings = self._compute(defaults=defaults)
        self._assert_todays_opus_rule(result)
        self.assertTrue(any("not a family word" in w for w in warnings), warnings)

    def test_junk_is_ignored_with_a_warning(self):
        for junk in ({"defaults": ["opus"]},
                     {"defaults": {"opus": 5}},
                     {"defaults": {"opus": "x" * 65}},
                     {"defaults": {"opus": "Opus\n::error::5.5"}},
                     {"defaults": {f"a{i}": "Opus 5.5" for i in range(17)}}):
            with self.subTest(junk=str(junk)[:40]):
                doc = {**self.DEFAULTS, **junk}
                result, warnings = self._compute(defaults=doc)
                self.assertNotIn("claude-opus-5-5", self._arms(result))
                self.assertTrue(warnings)
                self.assertFalse(any("::error::" in w for w in warnings), warnings)
                self.assertNotIn("::error::", json.dumps(result))


class TestNoDefaultsIsByteForByteUnchanged(_RosterFixture):

    def test_absent_empty_and_errored_docs_change_nothing(self):
        baseline, _ = self._compute()
        for doc in (None, {},
                    {**self.DEFAULTS, "defaults": {}, "error": "HTTP 503"},
                    {**self.DEFAULTS, "error": "URLError"},
                    {**self.DEFAULTS, "defaults": {}, "error": None},
                    "not a mapping"):
            with self.subTest(doc=str(doc)[:40]):
                result, _ = self._compute(defaults=doc)
                self.assertEqual(json.dumps(result, sort_keys=True),
                                 json.dumps(baseline, sort_keys=True))

    def test_an_errored_doc_says_so_in_a_warning(self):
        _, warnings = self._compute(defaults={**self.DEFAULTS, "defaults": {},
                                              "error": "HTTP 503"})
        self.assertTrue(any("HTTP 503" in w for w in warnings), warnings)


class TestSupersededExitWeeksPolicy(unittest.TestCase):

    def test_the_shipped_policy_sets_one_week(self):
        policy = roster.load_policy(POLICY)
        self.assertEqual(policy["superseded_exit_weeks"], 1)
        roster.validate_policy(policy)
        self.assertIn("#202", POLICY.read_text(encoding="utf-8"))

    def test_bad_values_fail_by_name(self):
        base = roster.load_policy(POLICY)
        for bad, label in ((None, "missing"), (-1, "negative"), (True, "bool"),
                           ("1", "string"), (1.0, "float"), (None, "None")):
            policy = dict(base)
            if label == "missing":
                del policy["superseded_exit_weeks"]
            else:
                policy["superseded_exit_weeks"] = bad
            with self.subTest(bad=label):
                with self.assertRaises(ValueError) as ctx:
                    roster.validate_policy(policy)
                self.assertIn("superseded_exit_weeks", str(ctx.exception))


class TestMainReadsDefaults(_RosterFixture):

    def test_main_passes_defaults_through(self):
        tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
        (tmp / "models.json").write_text(json.dumps(self._models_doc()), encoding="utf-8")
        (tmp / "census.json").write_text(json.dumps(self._census()), encoding="utf-8")
        (tmp / "defaults.json").write_text(json.dumps(self.DEFAULTS), encoding="utf-8")
        (tmp / "previous.yml").write_text(yaml.safe_dump(self.PREVIOUS), encoding="utf-8")
        now = self.NOW

        class Frozen(datetime):
            @classmethod
            def now(cls, tz=None):
                return now

        argv = ["roster.py", "--models", str(tmp / "models.json"),
                "--census", str(tmp / "census.json"),
                "--previous", str(tmp / "previous.yml"),
                "--defaults", str(tmp / "defaults.json"),
                "--out", str(tmp / "out.json")]
        with mock.patch.object(sys, "argv", argv), \
             mock.patch.object(roster, "datetime", Frozen), \
             contextlib.redirect_stdout(io.StringIO()), \
             contextlib.redirect_stderr(io.StringIO()):
            rc = roster.main()
        self.assertEqual(rc, 0)
        out = json.loads((tmp / "out.json").read_text(encoding="utf-8"))
        self.assertIn("claude-opus-5-5", [a["id"] for a in out["arms"]])


class TestWorkflowFetchesDefaults(unittest.TestCase):

    def _roster_step(self):
        doc = yaml.safe_load(EVAL_WORKFLOW.read_text(encoding="utf-8"))
        return next(s for s in doc["jobs"]["eval"]["steps"]
                    if "roster" in (s.get("name") or "").lower())["run"]

    def test_the_roster_step_fetches_defaults_first_and_passes_them(self):
        script = self._roster_step()
        fetch_at = script.index("scripts/fetch_model_defaults.py")
        roster_at = script.index("harness/roster.py")
        self.assertLess(fetch_at, roster_at)
        self.assertIn('--out "$work/defaults.json"', script[fetch_at:roster_at])
        self.assertIn('--defaults "$work/defaults.json"', script[roster_at:])
        self.assertNotIn("${{", script)

    def test_the_fetch_cannot_fail_the_step(self):
        script = self._roster_step()
        line = next(ln for ln in script.splitlines()
                    if "scripts/fetch_model_defaults.py" in ln)
        self.assertTrue(line.rstrip().endswith("|| true")
                        or line.lstrip().startswith("if "), line)


if __name__ == "__main__":
    unittest.main()
