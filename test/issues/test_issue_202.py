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
import http.client
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
import urllib.error
from datetime import datetime, timedelta, timezone
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
import render_roster_yaml  # noqa: E402


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

    def _raising(self, exc):
        def boom(request, timeout=None):
            raise exc
        out = self.tmp / "defaults.json"
        err = io.StringIO()
        with mock.patch.object(sys, "argv", ["x", "--out", str(out)]), \
             mock.patch("urllib.request.urlopen", boom), \
             contextlib.redirect_stderr(err), \
             contextlib.redirect_stdout(io.StringIO()):
            rc = fetch_model_defaults.main()
        return rc, out, err.getvalue()

    def test_an_http_protocol_error_still_writes_out(self):
        # F3 (#203 round 1): IncompleteRead is an HTTPException, not an
        # OSError, and used to escape as a traceback with no --out written.
        rc, out, err = self._raising(http.client.IncompleteRead(b"secret partial"))
        self.assertEqual(rc, 0)
        doc = json.loads(out.read_text(encoding="utf-8"))
        self.assertEqual((doc["defaults"], doc["error"]), ({}, "IncompleteRead"))
        self.assertIn("IncompleteRead", err)
        self.assertNotIn("secret", err + out.read_text(encoding="utf-8"))

    def test_any_other_exception_still_writes_out(self):
        rc, out, err = self._raising(RuntimeError("secret detail"))
        self.assertEqual(rc, 0)
        doc = json.loads(out.read_text(encoding="utf-8"))
        self.assertEqual((doc["defaults"], doc["error"]), ({}, "RuntimeError"))
        self.assertIn("RuntimeError", err)
        self.assertNotIn("secret", err + out.read_text(encoding="utf-8"))

    def test_the_docstring_no_longer_says_ci_pins_the_cli(self):
        self.assertNotIn("CI's is pinned", fetch_model_defaults.__doc__)

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


class TestSeatedDefaultCanRetire(_RosterFixture):
    """F1 (#203 round 1): a vendor default that is ALREADY an arm is not
    kept forever by its own seat — it gets rule 3's exit check."""

    WEEKS = [f"2026-W{n:02d}" for n in range(36, 50)]
    NOW_DEC = datetime(2026, 12, 8, 12, tzinfo=timezone.utc)
    PREV = {**_RosterFixture.PREVIOUS,
            "arms": [{"id": "claude-sonnet-5"}, {"id": "claude-opus-5-5"}]}

    def _census_no_opus(self, generated_at="2026-12-07T06:00:00Z"):
        counts = {"claude-sonnet-5": {w: 900 for w in self.WEEKS},
                  "claude-haiku-4-5": {w: 100 for w in self.WEEKS}}
        return {"generated_at": generated_at, "weeks": [], "counts": counts}

    def test_a_seated_default_with_no_usage_retires_by_the_exit_bar(self):
        result, _ = self._compute(defaults=self.DEFAULTS, previous=self.PREV,
                                  census=self._census_no_opus(), now=self.NOW_DEC)
        self.assertNotIn("claude-opus-5-5", self._arms(result))
        why = self._reason(result, "claude-opus-5-5", "retired_since_last")
        self.assertIn("below the 2% exit bar for the last 8 weeks", why)
        self.assertIn("0.0%", why)

    def test_the_same_on_a_stale_census_is_held(self):
        # Generated 2026-11-10: past the 14-day freshness window by 12-08.
        result, _ = self._compute(defaults=self.DEFAULTS, previous=self.PREV,
                                  census=self._census_no_opus("2026-11-10T06:00:00Z"),
                                  now=self.NOW_DEC)
        self.assertIn("claude-opus-5-5", self._arms(result))
        self.assertEqual(
            [r for r in result["retired_since_last"] if r["id"] == "claude-opus-5-5"], [])

    def test_a_seated_default_over_the_exit_bar_is_held(self):
        census = self._census_no_opus()
        census["counts"]["claude-opus-5-5"] = {w: 40 for w in self.WEEKS}
        result, _ = self._compute(defaults=self.DEFAULTS, previous=self.PREV,
                                  census=census, now=self.NOW_DEC)
        self.assertIn("claude-opus-5-5", self._arms(result))
        why = self._reason(result, "claude-opus-5-5")
        self.assertIn("at or above the 2% exit bar", why)
        self.assertIn("vendor default for the opus tier", why)

    def test_its_own_seat_is_not_a_previous_arm_in_the_tier(self):
        result, _ = self._compute(defaults=self.DEFAULTS, previous=self.PREV,
                                  census=self._census_no_opus(), now=self.NOW_DEC)
        for entry in result["arms"] + result["excluded"]:
            self.assertNotIn("previous arm `claude-opus-5-5` is in it", entry["reason"])


class TestPreviewArmGetsTheExitCheck(_RosterFixture):
    """F2(b) (#203 round 1): a previous arm NEWER than its tier's default is
    no longer retired on sight — it gets rule 3's exit check. It still
    earns no NEW seat."""

    WEEKS = [f"2026-W{n:02d}" for n in range(33, 42)]
    NOW_OCT = datetime(2026, 10, 12, 12, tzinfo=timezone.utc)
    D = {**_RosterFixture.DEFAULTS, "defaults": {"opus": "Opus 5.5", "sonnet": "Sonnet 5"}}
    PREV = {**_RosterFixture.PREVIOUS,
            "arms": [{"id": "claude-opus-5-5"}, {"id": "claude-opus-5-6"},
                     {"id": "claude-sonnet-5"}]}

    def _models(self):
        return self._models_doc(extra=[self._model(
            "claude-opus-5-6", "Claude Opus 5.6", "2026-10-01T00:00:00Z")])

    def _census(self, opus56=0, generated_at="2026-10-12T06:00:00Z"):
        counts = {"claude-sonnet-5": {w: 500 for w in self.WEEKS},
                  "claude-opus-5-5": {w: 450 for w in self.WEEKS},
                  "claude-haiku-4-5": {w: 50 for w in self.WEEKS}}
        if opus56:
            counts["claude-opus-5-6"] = {w: opus56 for w in self.WEEKS}
        return {"generated_at": generated_at, "weeks": [], "counts": counts}

    def test_a_heavily_used_preview_arm_is_held_not_retired(self):
        # The reviewer's a2.py: ~28% usage must not retire it.
        result, _ = self._compute(defaults=self.D, previous=self.PREV,
                                  models=self._models(), census=self._census(400),
                                  now=self.NOW_OCT)
        self.assertIn("claude-opus-5-6", self._arms(result))
        self.assertIn("claude-opus-5-5", self._arms(result))
        why = self._reason(result, "claude-opus-5-6")
        self.assertIn("held over from the previous roster", why)
        self.assertIn("at or above the 2% exit bar", why)
        self.assertEqual(result["retired_since_last"], [])

    def test_an_unused_preview_arm_retires_by_the_exit_bar(self):
        result, _ = self._compute(defaults=self.D, previous=self.PREV,
                                  models=self._models(), census=self._census(),
                                  now=self.NOW_OCT)
        self.assertNotIn("claude-opus-5-6", self._arms(result))
        why = self._reason(result, "claude-opus-5-6", "retired_since_last")
        self.assertIn("below the 2% exit bar", why)

    def test_a_stale_census_holds_a_preview_arm(self):
        result, _ = self._compute(defaults=self.D, previous=self.PREV,
                                  models=self._models(),
                                  census=self._census(generated_at="2026-09-20T06:00:00Z"),
                                  now=self.NOW_OCT)
        self.assertIn("claude-opus-5-6", self._arms(result))
        self.assertIn("no evidence to retire it", self._reason(result, "claude-opus-5-6"))

    def test_a_preview_that_is_not_a_previous_arm_still_earns_no_seat(self):
        previous = {**self.PREV, "arms": [{"id": "claude-opus-5-5"},
                                          {"id": "claude-sonnet-5"}]}
        result, _ = self._compute(defaults=self.D, previous=previous,
                                  models=self._models(), census=self._census(400),
                                  now=self.NOW_OCT)
        self.assertNotIn("claude-opus-5-6", self._arms(result))
        self.assertIn("newer than the vendor default",
                      self._reason(result, "claude-opus-5-6", "excluded"))


class TestCarriedDefaults(_RosterFixture):
    """F2(a) (#203 round 1): the committed roster carries the last resolved
    defaults, and a run whose docs read fails uses them instead of
    flip-flopping to newest-in-tier."""

    CARRIED = {"source": "https://code.claude.com/docs/en/model-config.md",
               "fetched_at": "2026-09-27T10:00:00Z",
               "resolved": {"opus": "claude-opus-5-5", "sonnet": "claude-sonnet-5"}}
    DOWN = {**_RosterFixture.DEFAULTS, "defaults": {}, "error": "HTTP 503"}

    def _previous(self, arms=("claude-sonnet-5", "claude-opus-5"), carried=None):
        return {**self.PREVIOUS, "arms": [{"id": a} for a in arms],
                "defaults": copy.deepcopy(self.CARRIED if carried is None else carried)}

    def test_a_failed_read_uses_the_carried_defaults(self):
        result, warnings = self._compute(defaults=self.DOWN, previous=self._previous())
        self.assertIn("claude-opus-5-5", self._arms(result))
        why = self._reason(result, "claude-opus-5-5")
        self.assertIn("last read 2026-09-27T10:00:00Z", why)
        self.assertIn("HTTP 503", why)
        self.assertIn("vendor default for the opus tier", why)
        self.assertIs(result["defaults"]["carried"], True)
        self.assertEqual(result["defaults"]["resolved"], self.CARRIED["resolved"])
        self.assertEqual(result["defaults"]["fetched_at"], "2026-09-27T10:00:00Z")
        self.assertTrue(any("carried" in w for w in warnings), warnings)
        self.assertIn("this run's read failed", roster.render_summary(result))

    def test_an_absent_doc_uses_the_carried_defaults(self):
        result, _ = self._compute(defaults=None, previous=self._previous())
        self.assertIn("claude-opus-5-5", self._arms(result))
        self.assertIs(result["defaults"]["carried"], True)

    def test_a_good_read_is_not_carried(self):
        result, _ = self._compute(defaults=self.DEFAULTS, previous=self._previous())
        self.assertNotIn("carried", result["defaults"])

    def test_a_carried_id_no_longer_available_is_dropped(self):
        result, warnings = self._compute(
            defaults=self.DOWN, previous=self._previous(),
            models=self._models_doc(drop=("claude-opus-5-5",)))
        self.assertNotIn("opus", result["defaults"]["resolved"])
        self.assertEqual(result["defaults"]["resolved"], {"sonnet": "claude-sonnet-5"})
        self.assertTrue(any("`opus`" in w and "carried" in w for w in warnings), warnings)

    def test_a_carried_id_in_another_tier_is_dropped(self):
        carried = {**self.CARRIED, "resolved": {"opus": "claude-sonnet-5"}}
        result, warnings = self._compute(defaults=self.DOWN,
                                         previous=self._previous(carried=carried))
        self.assertNotIn("opus", (result.get("defaults") or {}).get("resolved", {}))
        self.assertTrue(any("`opus`" in w for w in warnings), warnings)

    def test_a_docs_outage_after_a_retirement_does_not_reseat_it(self):
        # The reviewer's a7.py: opus-5 retired with the docs up; the next
        # run's docs outage must not bring it back by rule 1.
        census = self._later_census(opus5_w40=5, opus55_w40=440)
        first, _ = self._compute(
            defaults=self.DEFAULTS, census=census, now=self.LATER,
            previous={**self.PREVIOUS, "arms": [{"id": "claude-sonnet-5"},
                                                {"id": "claude-opus-5"},
                                                {"id": "claude-opus-5-5"}]})
        self.assertNotIn("claude-opus-5", self._arms(first))
        committed = yaml.safe_load(render_roster_yaml.render(first, "1", "abc"))
        self.assertEqual(roster.committed_roster_problems(committed), [])
        second, _ = self._compute(defaults=self.DOWN, census=census,
                                  now=self.LATER, previous=committed)
        self.assertEqual(sorted(self._arms(second)),
                         ["claude-opus-5-5", "claude-sonnet-5"])

    def test_a_docs_outage_does_not_seat_an_unmade_default(self):
        # The reviewer's a2.py week 1, with a carried block: opus-5-6 is
        # newest but not the default, so it takes no seat.
        models = self._models_doc(extra=[self._model(
            "claude-opus-5-6", "Claude Opus 5.6", "2026-10-01T00:00:00Z")])
        weeks = [f"2026-W{n:02d}" for n in range(33, 42)]
        census = {"generated_at": "2026-10-12T06:00:00Z", "weeks": [], "counts": {
            "claude-sonnet-5": {w: 500 for w in weeks},
            "claude-opus-5-5": {w: 450 for w in weeks},
            "claude-haiku-4-5": {w: 50 for w in weeks}}}
        result, _ = self._compute(
            defaults=self.DOWN, models=models, census=census,
            now=datetime(2026, 10, 12, 12, tzinfo=timezone.utc),
            # Read a week earlier: CARRIED's own date is past the 14-day
            # `defaults_carry_max_age_days` by 10-12 (#203 round 2).
            previous=self._previous(arms=("claude-sonnet-5", "claude-opus-5-5"),
                                    carried={**self.CARRIED,
                                             "fetched_at": "2026-10-05T10:00:00Z"}))
        self.assertEqual(sorted(self._arms(result)),
                         ["claude-opus-5-5", "claude-sonnet-5"])

    def test_the_rendered_roster_carries_the_defaults_block(self):
        result, _ = self._compute(defaults=self.DEFAULTS)
        document = yaml.safe_load(render_roster_yaml.render(result, "1", "abc"))
        self.assertEqual(document["defaults"],
                         {"source": self.DEFAULTS["source"],
                          "fetched_at": "2026-09-27T10:00:00Z",
                          "resolved": {"opus": "claude-opus-5-5",
                                       "sonnet": "claude-sonnet-5"}})
        self.assertEqual(roster.committed_roster_problems(document), [])
        carried, _ = self._compute(defaults=self.DOWN, previous={
            **self.PREVIOUS, "defaults": document["defaults"]})
        document = yaml.safe_load(render_roster_yaml.render(carried, "1", "abc"))
        self.assertIs(document["defaults"]["carried"], True)
        self.assertEqual(roster.committed_roster_problems(document), [])

    def test_a_changed_resolution_is_a_material_proposal(self):
        # Otherwise the block could never reach the committed roster on a
        # run whose arms happen not to move.
        prev = {**self.PREVIOUS, "arms": [{"id": "claude-sonnet-5"},
                                          {"id": "claude-opus-5-5"}]}
        census = self._later_census(opus5_w40=5, opus55_w40=440)
        result, _ = self._compute(defaults=self.DEFAULTS, previous=prev,
                                  census=census, now=self.LATER)
        change = [c for c in result["proposal"]["changes"]
                  if c["field"] == "defaults.resolved"]
        self.assertEqual(len(change), 1, result["proposal"]["changes"])
        self.assertEqual(change[0]["to"], self.CARRIED["resolved"])
        self.assertEqual(result["proposal"]["status"], "differs")
        # The same resolution already committed proposes nothing about it.
        result, _ = self._compute(defaults=self.DEFAULTS, census=census,
                                  now=self.LATER,
                                  previous={**prev, "defaults": self.CARRIED})
        self.assertEqual([c for c in result["proposal"]["changes"]
                          if c["field"] == "defaults.resolved"], [])

    def test_no_doc_renders_no_defaults_block(self):
        result, _ = self._compute()
        self.assertNotIn("defaults:", render_roster_yaml.render(result, "1", "abc"))

    def test_the_committed_block_is_type_checked(self):
        base = yaml.safe_load((REPO_ROOT / "evals" / "roster.yml").read_text(encoding="utf-8"))
        good = {**base, "defaults": copy.deepcopy(self.CARRIED)}
        self.assertEqual(roster.committed_roster_problems(good), [])
        bad_blocks = {
            "not a mapping": ["opus"],
            "resolved not a mapping": {**self.CARRIED, "resolved": ["opus"]},
            "alias off the ladder": {**self.CARRIED, "resolved": {"opusplan": "claude-opus-5-5"}},
            "alias badly shaped": {**self.CARRIED, "resolved": {"Opus!": "claude-opus-5-5"}},
            "id not an id": {**self.CARRIED, "resolved": {"opus": "Opus 5.5 ::error::"}},
            "too many": {**self.CARRIED, "resolved": {f"a{i}": "claude-opus-5-5"
                                                      for i in range(17)}},
            "source junk": {**self.CARRIED, "source": "x::error::y"},
            "fetched_at junk": {**self.CARRIED, "fetched_at": "yesterday"},
            "carried not bool": {**self.CARRIED, "carried": "yes"},
            "unknown key": {**self.CARRIED, "extra": 1},
        }
        for label, block in bad_blocks.items():
            with self.subTest(label):
                self.assertNotEqual(
                    roster.committed_roster_problems({**base, "defaults": block}), [])


class TestUnresolvedDefaultsFallBack(_RosterFixture):
    """Every way a default can fail to resolve leaves its tier on today's
    rule — the cooling-off included — and says so in a warning."""

    @staticmethod
    def _policy(**overrides):
        # A POSITIVE cooling-off, supplied rather than read: the shipped
        # value is 0 since the owner's decision of 2026-09-27 (#202), and
        # these tests pin that an unresolved default leaves its tier on the
        # rule that applies the cooling-off whenever one is configured.
        return _RosterFixture._policy(**{"cooling_off_days": 7, **overrides})

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


class TestAliasConflicts(_RosterFixture):
    """F7 (#203 round 1), revised by R2-4 (#203 round 2): an alias resolves
    only to a model of its OWN family word. Two peer aliases in one rung
    (`fable`, `mythos`) are two families, not a conflict; a peer alias
    naming another family's model is unresolved on its own. A conflict is
    two spellings of the SAME family word naming different models."""

    def test_a_peer_alias_naming_another_family_is_unresolved_alone(self):
        defaults = {**self.DEFAULTS, "defaults": {"fable": "Fable 5.1",
                                                  "mythos": "Fable 5"}}
        result, warnings = self._compute(defaults=defaults)
        self.assertEqual(result["defaults"]["resolved"], {"fable": "claude-fable-5-1"})
        self.assertEqual([u["alias"] for u in result["defaults"]["unresolved"]],
                         ["mythos"])
        self.assertTrue(any("`mythos`" in w and "fable family" in w
                            for w in warnings), warnings)

    def test_peer_aliases_naming_their_own_families_both_resolve(self):
        models = self._models_doc(extra=[self._model(
            "claude-mythos-1", "Claude Mythos 1", "2026-09-20T00:00:00Z")])
        defaults = {**self.DEFAULTS, "defaults": {"fable": "Fable 5.1",
                                                  "mythos": "Mythos 1"}}
        result, _ = self._compute(defaults=defaults, models=models)
        self.assertEqual(result["defaults"]["resolved"],
                         {"fable": "claude-fable-5-1", "mythos": "claude-mythos-1"})
        self.assertEqual(result["defaults"]["unresolved"], [])

    def test_a_third_peer_off_its_family_does_not_block_the_others(self):
        policy = self._policy(tiers=["haiku", "sonnet", "opus",
                                     ["fable", "mythos", "fablex"]])
        defaults = {**self.DEFAULTS, "defaults": {"fable": "Fable 5.1",
                                                  "mythos": "Fable 5",
                                                  "fablex": "Fable 5.1"}}
        result, _ = self._compute(defaults=defaults, policy=policy)
        self.assertEqual(result["defaults"]["resolved"], {"fable": "claude-fable-5-1"})
        self.assertEqual(sorted(u["alias"] for u in result["defaults"]["unresolved"]),
                         ["fablex", "mythos"])

    def test_case_duplicates_naming_different_models_conflict(self):
        defaults = {**self.DEFAULTS, "defaults": {"OPUS": "Opus 5", "opus": "Opus 5.5"}}
        result, warnings = self._compute(defaults=defaults)
        self.assertNotIn("opus", result["defaults"]["resolved"])
        self.assertIn("opus", [u["alias"] for u in result["defaults"]["unresolved"]])
        self.assertTrue(any("`opus`" in w for w in warnings), warnings)
        self.assertNotIn("vendor default", self._reason(result, "claude-opus-5-5"))

    def test_case_duplicates_naming_the_same_model_dedupe_silently(self):
        defaults = {**self.DEFAULTS, "defaults": {"OPUS": "Opus 5.5", "opus": "Opus 5.5"}}
        result, warnings = self._compute(defaults=defaults)
        self.assertEqual(result["defaults"]["resolved"], {"opus": "claude-opus-5-5"})
        self.assertEqual(result["defaults"]["unresolved"], [])
        self.assertEqual(warnings, [])


class TestPreflightWordingAtAPositiveCoolingOff(_RosterFixture):
    """F6 (#203 round 1): at a positive cooling-off the preflight reason is
    origin/main's, word for word; only at 0 does the new wording apply."""

    def test_a_positive_cooling_off_keeps_the_old_wording(self):
        for days in (7, 3):
            with self.subTest(days=days):
                result, _ = self._compute(policy=self._policy(cooling_off_days=days))
                self.assertEqual(
                    result["preflight"]["reason"],
                    f"newest model in the haiku tier that is past the {days}-day "
                    f"cooling-off: the lowest tier the Models API still returns, "
                    f"and this is its cheapest safely-invocable pick")

    def test_zero_uses_the_new_wording(self):
        result, _ = self._compute(policy=self._policy(cooling_off_days=0))
        self.assertEqual(
            result["preflight"]["reason"],
            "newest model in the haiku tier (no cooling-off applies: "
            "`cooling_off_days` is 0): the lowest tier the Models API still "
            "returns, and this is its cheapest safely-invocable pick")


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


class TestRosterOnlyDispatch(unittest.TestCase):
    """A dispatch can refresh and propose the roster WITHOUT a paid eval run:
    the owner held paid runs until the roster seats the new defaults, and the
    roster step exists only inside this workflow."""

    SKIPPED = ("WIF auth preflight", "Run the eval (both arms, judge)",
               "Build the badge over the run window, commit, and push")
    KEPT = ("Mint OIDC token and exchange for Anthropic access token",
            "Refresh the model roster", "Propose a roster change")

    def setUp(self):
        doc = yaml.safe_load(EVAL_WORKFLOW.read_text(encoding="utf-8"))
        # PyYAML reads the bare `on:` key as boolean True.
        self.triggers = doc.get("on", doc.get(True))
        self.steps = {s.get("name"): s for s in doc["jobs"]["eval"]["steps"]}

    def test_the_input_is_a_boolean_that_defaults_off(self):
        spec = self.triggers["workflow_dispatch"]["inputs"]["roster_only"]
        self.assertEqual(spec.get("type"), "boolean")
        self.assertIs(spec.get("default"), False)

    def test_the_paid_steps_are_skipped_in_roster_only_mode(self):
        for name in self.SKIPPED:
            with self.subTest(step=name):
                self.assertIn(name, self.steps)
                self.assertEqual(self.steps[name].get("if"),
                                 "${{ !inputs.roster_only }}")

    def test_the_roster_steps_still_run(self):
        for name in self.KEPT:
            with self.subTest(step=name):
                self.assertIn(name, self.steps)
                self.assertNotIn("roster_only", str(self.steps[name].get("if", "")))

    def test_the_input_never_reaches_a_run_block(self):
        # Never interpolated: the one run block that reads it does so from
        # $GITHUB_EVENT_PATH with jq, at run time (#203 round 1).
        for name, step in self.steps.items():
            with self.subTest(step=name):
                run = step.get("run", "")
                self.assertNotIn("${{ inputs.roster_only", run)
                self.assertNotIn("${{ !inputs.roster_only", run)
                self.assertNotIn("github.event.inputs", run)
                for line in run.splitlines():
                    if "roster_only" in line and ".inputs.roster_only" in line:
                        self.assertIn('"$GITHUB_EVENT_PATH"', line)

    NOTE_START = "# >>> roster-only note"
    NOTE_END = "# <<< roster-only note"

    def _note_fragment(self):
        run = self.steps["Propose a roster change"]["run"]
        self.assertIn(self.NOTE_START, run)
        start = run.index(self.NOTE_START)
        end = run.index(self.NOTE_END)
        return run[start:end]

    def _eval_note(self, event):
        tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
        (tmp / "event.json").write_text(json.dumps(event), encoding="utf-8")
        script = ("set -euo pipefail\n" + self._note_fragment()
                  + '\nprintf "%s" "$eval_note"\n')
        done = subprocess.run(["bash", "-c", script], capture_output=True,
                              text=True, timeout=30,
                              env={"PATH": os.environ.get("PATH", ""),
                                   "GITHUB_EVENT_PATH": str(tmp / "event.json")})
        self.assertEqual(done.returncode, 0, done.stderr)
        return done.stdout

    @unittest.skipUnless(shutil.which("jq") and shutil.which("bash"), "needs jq and bash")
    def test_a_roster_only_run_does_not_claim_an_eval_ran(self):
        for value in (True, "true"):
            with self.subTest(value=value):
                note = self._eval_note({"inputs": {"roster_only": value}})
                self.assertIn("no eval ran", note)
                self.assertIn("nothing from this run is published to `eval-results`", note)
                self.assertNotIn("results will still be published", note)

    @unittest.skipUnless(shutil.which("jq") and shutil.which("bash"), "needs jq and bash")
    def test_a_normal_run_says_the_eval_ran_on_the_committed_roster(self):
        for event in ({"inputs": {"roster_only": False}},
                      {"inputs": {"roster_only": "false"}},
                      {"inputs": {"fixture": "evals/x"}}, {"schedule": "0 7 * * 1"}):
            with self.subTest(event=event):
                note = self._eval_note(event)
                self.assertIn("ran on the committed", note)
                self.assertNotIn("no eval ran", note)

    def test_both_bodies_carry_the_note(self):
        run = self.steps["Propose a roster change"]["run"]
        self.assertNotIn("The paid eval ran on the committed", run.replace(
            self._note_fragment(), ""))
        self.assertGreaterEqual(run.count('"$eval_note"'), 2)

    def test_the_input_and_readme_say_nothing_is_published(self):
        spec = self.triggers["workflow_dispatch"]["inputs"]["roster_only"]
        for text in (spec["description"],
                     (REPO_ROOT / "README.md").read_text(encoding="utf-8")):
            flat = " ".join(text.split())
            self.assertIn("publishes nothing to `eval-results`", flat)
            self.assertIn("`roster/proposal`", flat)


# --- #203 round 2 ------------------------------------------------------------

DOCS_URL = "https://code.claude.com/docs/en/model-config.md"


class _WeeklyLoop(_RosterFixture):
    """The real week-by-week loop, inline and hermetic (#203 round 2): every
    Monday at 12:00 compute the roster against a census generated at 06:00
    over the twelve complete weeks before it, render the proposal, check it
    against the committed-roster contract, and feed it back as `previous`
    whenever its status is "differs" — i.e. a human merges every proposal."""

    BASE = [
        _RosterFixture._model("claude-haiku-4-5", "Claude Haiku 4.5", "2025-10-01T00:00:00Z"),
        _RosterFixture._model("claude-sonnet-5", "Claude Sonnet 5", "2026-02-01T00:00:00Z"),
        _RosterFixture._model("claude-opus-5", "Claude Opus 5", "2026-04-01T00:00:00Z"),
        _RosterFixture._model("claude-opus-5-5", "Claude Opus 5.5", "2026-09-26T12:00:00Z"),
        _RosterFixture._model("claude-fable-5-1", "Claude Fable 5.1", "2026-09-01T00:00:00Z"),
    ]
    PREV0 = {"schema": 1,
             "arms": [{"id": "claude-sonnet-5"}, {"id": "claude-opus-5"}],
             "judge": {"id": "claude-fable-5-1", "is_arm": False},
             "preflight": {"id": "claude-haiku-4-5"},
             "catalogue_seen": [],
             "provenance": {"seeded": "x", "from": "y"},
             "generated_at": "2026-09-21T00:00:00Z"}
    #: Monday of 2026-W40.
    START = datetime(2026, 9, 28, tzinfo=timezone.utc)
    ERR = {"fetched_at": None, "source": DOCS_URL, "defaults": {},
           "error": "HTTPError 503"}

    @staticmethod
    def _week_number(label):
        year, week = label.split("-W")
        return (int(year) - 2026) * 53 + int(week)

    def _docs(self, k, **defaults):
        fetched = (self.START + timedelta(weeks=k, hours=11)).strftime("%Y-%m-%dT%H:%M:%SZ")
        return {"fetched_at": fetched, "source": DOCS_URL,
                "defaults": defaults or {"opus": "Opus 5.5", "sonnet": "Sonnet 5"},
                "error": None}

    def _loop(self, usage, weeks, docs_for, previous=None, models=None):
        prev = copy.deepcopy(previous or self.PREV0)
        out = []
        for k in range(weeks):
            now = self.START + timedelta(weeks=k, hours=12)
            counts: dict = {}
            for back in range(12, 0, -1):
                label = timeweeks.iso_week(now - timedelta(weeks=back))
                for model_id, n in usage(self._week_number(label)).items():
                    counts.setdefault(model_id, {})[label] = n
            census = {"generated_at": (self.START + timedelta(weeks=k, hours=6))
                      .strftime("%Y-%m-%dT%H:%M:%SZ"), "weeks": [], "counts": counts}
            warnings: list[str] = []
            committed = copy.deepcopy(prev)
            result = roster.compute_roster(
                models_doc={"fetched_at": now.isoformat(),
                            "models": list(models or self.BASE)},
                census_doc=census, policy=self._policy(), previous=copy.deepcopy(prev),
                now=now, warn=warnings.append, defaults_doc=docs_for(k))
            out.append({"result": result, "warnings": warnings, "committed": committed})
            if result["proposal"]["status"] == "differs":
                prev = yaml.safe_load(render_roster_yaml.render(result, "1", "abc"))
                self.assertEqual(roster.committed_roster_problems(prev), [], k)
        return out, prev


class TestCarriedDefaultsExpire(_RosterFixture):
    """R2-1 (#203 round 2): carried defaults expire after
    `defaults_carry_max_age_days`, drop a tier on staleness evidence, and
    are loud whenever they are used."""

    CARRIED = TestCarriedDefaults.CARRIED
    DOWN = TestCarriedDefaults.DOWN

    def _previous(self, **block):
        return {**self.PREVIOUS, "defaults": {**copy.deepcopy(self.CARRIED), **block}}

    def test_the_shipped_policy_sets_fourteen_days_and_cites_203(self):
        policy = roster.load_policy(POLICY)
        self.assertEqual(policy["defaults_carry_max_age_days"], 14)
        roster.validate_policy(policy)
        text = POLICY.read_text(encoding="utf-8")
        at = text.index("defaults_carry_max_age_days:")
        self.assertIn("#203", text[max(0, at - 1500):at])

    def test_bad_max_age_values_fail_by_name(self):
        base = roster.load_policy(POLICY)
        for bad in ("missing", 0, -1, True, "14", 1.5, None):
            policy = dict(base)
            if bad == "missing":
                del policy["defaults_carry_max_age_days"]
            else:
                policy["defaults_carry_max_age_days"] = bad
            with self.subTest(bad=bad):
                with self.assertRaises(ValueError) as ctx:
                    roster.validate_policy(policy)
                self.assertIn("defaults_carry_max_age_days", str(ctx.exception))

    def test_a_carry_past_the_max_age_is_not_used(self):
        now = datetime(2026, 10, 17, 12, tzinfo=timezone.utc)  # 20 days on
        census = self._census(generated_at="2026-10-12T06:00:00Z")
        result, warnings = self._compute(defaults=self.DOWN, previous=self._previous(),
                                         census=census, now=now)
        defaults = result["defaults"]
        self.assertEqual(defaults["resolved"], {})
        self.assertNotIn("carried", defaults)
        self.assertIs(defaults["carried_expired"], True)
        for part in ("HTTP 503", "2026-09-27T10:00:00Z", "20 days", "expired"):
            self.assertIn(part, defaults["carried_reason"])
        self.assertNotIn("vendor default", self._reason(result, "claude-opus-5-5"))
        self.assertIn("newest model in the opus tier", self._reason(result, "claude-opus-5-5"))
        expired = [w for w in warnings if "expired" in w]
        self.assertEqual(len(expired), 1, warnings)
        self.assertIn("2026-09-27T10:00:00Z", expired[0])
        change = [c for c in result["proposal"]["changes"]
                  if c["field"] == "defaults.resolved"]
        self.assertEqual(len(change), 1)
        self.assertIsNone(change[0]["to"])
        self.assertIn("expired", change[0]["reason"])
        self.assertEqual(result["proposal"]["status"], "differs")

    def test_a_carry_exactly_at_the_max_age_is_still_used(self):
        now = datetime(2026, 10, 11, 12, tzinfo=timezone.utc)  # 14 days, 2 hours
        census = self._census(generated_at="2026-10-10T06:00:00Z")
        result, _ = self._compute(defaults=self.DOWN, previous=self._previous(),
                                  census=census, now=now)
        self.assertIs(result["defaults"]["carried"], True)
        self.assertIn("14 days", result["defaults"]["carried_reason"])

    def test_a_newer_model_over_the_entry_bar_drops_the_carried_default(self):
        models = self._models_doc(extra=[self._model(
            "claude-opus-6", "Claude Opus 6", "2026-09-27T00:00:00Z")])
        census = self._census(extra={"claude-opus-6": {w: 300 for w in self.ENTER}})
        result, warnings = self._compute(defaults=self.DOWN, previous=self._previous(),
                                         models=models, census=census)
        self.assertEqual(result["defaults"]["resolved"], {"sonnet": "claude-sonnet-5"})
        why = next(u["reason"] for u in result["defaults"]["unresolved"]
                   if u["alias"] == "opus")
        self.assertIn("claude-opus-6", why)
        self.assertIn("claude-opus-6", self._arms(result))
        self.assertNotIn("claude-opus-5-5", self._arms(result))
        stale = [w for w in warnings if "claude-opus-6" in w and "claude-opus-5-5" in w]
        self.assertEqual(len(stale), 1, warnings)
        self.assertIs(result["defaults"]["carried"], True)

    def test_a_fresh_read_is_not_dropped_by_a_newer_models_usage(self):
        models = self._models_doc(extra=[self._model(
            "claude-opus-6", "Claude Opus 6", "2026-09-27T00:00:00Z")])
        census = self._census(extra={"claude-opus-6": {w: 300 for w in self.ENTER}})
        result, _ = self._compute(defaults=self.DEFAULTS, models=models, census=census)
        self.assertEqual(result["defaults"]["resolved"]["opus"], "claude-opus-5-5")
        self.assertNotIn("claude-opus-6", self._arms(result))

    def test_a_carried_run_says_so_first(self):
        result, _ = self._compute(defaults=self.DOWN, previous=self._previous())
        reason = result["defaults"]["carried_reason"]
        self.assertIn("HTTP 503", reason)
        self.assertIn("0 days", reason)
        head = roster.render_summary(result).splitlines()[:4]
        self.assertTrue(any(reason in line for line in head), head)

    def test_a_healthy_or_absent_run_is_not_flagged(self):
        for doc, prev in ((self.DEFAULTS, self._previous()), (None, self.PREVIOUS)):
            with self.subTest(doc=bool(doc)):
                result, _ = self._compute(defaults=doc, previous=prev)
                self.assertNotIn("carried_reason", result.get("defaults") or {})
                self.assertNotIn("carried", roster.render_summary(result).splitlines()[2])

    def test_s3_a_newer_default_takes_the_fleet_during_an_outage(self):
        # The reviewer's s3.py: docs good weeks 0-2, failing from week 3;
        # the vendor makes Opus 6 (released W43) the default in week 4 and
        # the fleet moves to it in W44.
        loop = _WeeklyLoop("run")
        models = loop.BASE + [self._model("claude-opus-6", "Claude Opus 6",
                                          "2026-10-20T12:00:00Z")]

        def usage(n):
            return {"claude-sonnet-5": 450, "claude-haiku-4-5": 60,
                    "claude-fable-5-1": 30,
                    "claude-opus-5": 0 if n >= 41 else 450,
                    "claude-opus-5-5": 0 if n >= 44 else (450 if n >= 41 else 0),
                    "claude-opus-6": 450 if n >= 44 else 0}

        out, _ = loop._loop(usage, 14, lambda k: loop._docs(k) if k < 3 else loop.ERR,
                            models=models)
        carried = [k for k, week in enumerate(out)
                   if "defaults" in week["committed"] and k >= 3]
        self.assertTrue(carried)
        for k in carried:
            defaults = out[k]["result"].get("defaults") or {}
            self.assertTrue(defaults.get("carried_reason"), (k, defaults))
            head = roster.render_summary(out[k]["result"]).splitlines()[:4]
            self.assertTrue(any(defaults["carried_reason"] in line for line in head), k)
        seated_at = next((k for k, week in enumerate(out)
                          if "claude-opus-6" in self._arms(week["result"])), None)
        self.assertIsNotNone(seated_at, "opus-6 was never seated")
        expiry = next(k for k, week in enumerate(out)
                      if (week["result"].get("defaults") or {}).get("carried_expired"))
        self.assertLessEqual(seated_at, expiry)
        for week in out[seated_at:]:
            self.assertIn("claude-opus-6", self._arms(week["result"]))
        self.assertNotIn("claude-opus-5-5", self._arms(out[-1]["result"]))


class TestCommittedBlockRecordsTheLastGoodRead(_RosterFixture):
    """R2-2 (#203 round 2): the committed `defaults.fetched_at` is the last
    SUCCESSFUL read, refreshed often enough that the carry age means
    something, and `carried` never outlives the outage."""

    CARRIED = TestCarriedDefaults.CARRIED
    DOWN = TestCarriedDefaults.DOWN

    def _committed(self, **block):
        first, _ = self._compute(defaults=self.DEFAULTS)
        doc = yaml.safe_load(render_roster_yaml.render(first, "1", "abc"))
        doc["defaults"].update(block)
        return doc

    def _again(self, days, defaults, committed):
        now = self.NOW + timedelta(days=days)
        doc = defaults
        if defaults is self.DEFAULTS:
            doc = {**self.DEFAULTS, "fetched_at": (now - timedelta(hours=1))
                   .strftime("%Y-%m-%dT%H:%M:%SZ")}
        census = self._census(generated_at="2026-10-03T06:00:00Z")
        return self._compute(defaults=doc, previous=committed, now=now, census=census)

    @staticmethod
    def _fields(result):
        return {c["field"] for c in result["proposal"]["changes"]}

    def test_a_healthy_fresh_read_proposes_nothing(self):
        committed = self._committed()
        result, _ = self._again(7, self.DEFAULTS, committed)
        self.assertEqual(result["proposal"]["status"], "same",
                         result["proposal"]["changes"])

    def test_a_healthy_read_past_half_the_max_age_refreshes_fetched_at(self):
        committed = self._committed()
        result, _ = self._again(8, self.DEFAULTS, committed)
        self.assertEqual(result["proposal"]["status"], "differs")
        self.assertIn("defaults.fetched_at", self._fields(result))
        document = yaml.safe_load(render_roster_yaml.render(result, "1", "abc"))
        self.assertEqual(document["defaults"]["fetched_at"], "2026-10-05T11:00:00Z")

    def test_starting_to_carry_is_material(self):
        result, _ = self._again(1, self.DOWN, self._committed())
        self.assertEqual(result["proposal"]["status"], "differs")
        self.assertIn("defaults.carried", self._fields(result))

    def test_a_healthy_read_after_an_outage_clears_carried(self):
        result, _ = self._again(1, self.DEFAULTS, self._committed(carried=True))
        self.assertEqual(result["proposal"]["status"], "differs")
        self.assertIn("defaults.carried", self._fields(result))
        document = yaml.safe_load(render_roster_yaml.render(result, "1", "abc"))
        self.assertIs(document["defaults"].get("carried", False), False)
        self.assertEqual(document["defaults"]["fetched_at"], "2026-09-28T11:00:00Z")

    def test_s8_a_later_outage_quotes_the_healthy_read(self):
        # The reviewer's s8.py: outages in weeks 1-2 and 9, healthy between.
        loop = _WeeklyLoop("run")

        def usage(n):
            return {"claude-sonnet-5": 450, "claude-haiku-4-5": 60,
                    "claude-fable-5-1": 30,
                    "claude-opus-5": 0 if n >= 41 else 450,
                    "claude-opus-5-5": 450 if n >= 41 else 0}

        out, final = loop._loop(usage, 10,
                                lambda k: loop.ERR if k in (1, 2, 9) else loop._docs(k))
        # After the first healthy read following the outage, the committed
        # block is no longer `carried`.
        self.assertIs(out[4]["committed"]["defaults"].get("carried", False), False)
        last_good = out[9]["committed"]["defaults"]["fetched_at"]
        self.assertGreaterEqual(last_good, "2026-10-19T11:00:00Z")
        reason = out[9]["result"]["defaults"]["carried_reason"]
        self.assertIn(last_good, reason)
        seat = self._reason(out[9]["result"], "claude-opus-5-5")
        self.assertIn(f"last read {last_good}", seat)
        self.assertTrue(any(last_good in w for w in out[9]["warnings"]))
        self.assertIs(final["defaults"]["carried"], True)
        self.assertEqual(final["defaults"]["fetched_at"], last_good)


class TestSeatedDefaultHeldByItsTier(_WeeklyLoop):
    """R2-3 (#203 round 2): a seated default with nothing else putting its
    tier on the roster is held while the TIER's combined share clears the
    exit bar, and a retirement quotes the tier's share."""

    def test_s5_a_tier_between_the_bars_keeps_an_arm(self):
        # The reviewer's s5.py: the opus tier at a steady ~5% (between the
        # 2% exit and 10% entry bars); the fleet switches to 5.5 in W40.
        def usage(n):
            return {"claude-sonnet-5": 900, "claude-haiku-4-5": 50,
                    "claude-fable-5-1": 0,
                    "claude-opus-5": 0 if n >= 40 else 50,
                    "claude-opus-5-5": 50 if n >= 40 else 0}

        out, _ = self._loop(usage, 5, self._docs)
        for k, week in enumerate(out):
            arms = self._arms(week["result"])
            self.assertTrue([a for a in arms if "opus" in a], (k, arms))
        for week in out[1:]:
            self.assertIn("claude-opus-5-5", self._arms(week["result"]))
        held = self._reason(out[1]["result"], "claude-opus-5-5")
        self.assertIn("opus tier's combined share", held)
        self.assertIn("at or above the 2% exit bar", held)

    def test_a_tier_under_the_exit_bar_retires_the_default_with_the_tier_share(self):
        weeks = [f"2026-W{n:02d}" for n in range(33, 41)]
        census = {"generated_at": "2026-10-05T06:00:00Z", "weeks": [], "counts": {
            "claude-sonnet-5": {w: 1000 for w in weeks},
            "claude-opus-5": {w: 5 for w in weeks},
            "claude-opus-5-5": {w: 5 for w in weeks}}}
        previous = {**self.PREVIOUS, "arms": [{"id": "claude-sonnet-5"},
                                              {"id": "claude-opus-5-5"}]}
        result, _ = self._compute(defaults=self.DEFAULTS, previous=previous,
                                  census=census,
                                  now=datetime(2026, 10, 5, 12, tzinfo=timezone.utc))
        self.assertNotIn("claude-opus-5-5", self._arms(result))
        why = self._reason(result, "claude-opus-5-5", "retired_since_last")
        self.assertIn("opus tier's combined share", why)
        self.assertIn("below the 2% exit bar for the last 8 weeks", why)
        change = next(c for c in result["proposal"]["changes"]
                      if c["from"] == "claude-opus-5-5")
        # 70 of 7070 over the seven census weeks in the window: both opus
        # models' turns, not the default's own 35.
        self.assertIn("70 of the window's 7070", change["reason"])
        self.assertIn("combined share", change["reason"])


class TestPeerFamilies(_RosterFixture):
    """R2-4 (#203 round 2): the vendor-default rules apply only to models
    of the default's own family word; a peer family in the same rung is
    decided by rules 1-3 as before."""

    def test_p9_a_peer_family_keeps_its_usage_seat(self):
        models = self._models_doc(extra=[self._model(
            "claude-mythos-1", "Claude Mythos 1", "2026-09-20T00:00:00Z")])
        weeks = ["2026-W37", "2026-W38", "2026-W39", "2026-W40"]
        census = {"generated_at": "2026-10-05T06:00:00Z", "weeks": [], "counts": {
            "claude-sonnet-5": {w: 400 for w in weeks},
            "claude-mythos-1": {w: 400 for w in weeks},
            "claude-opus-5-5": {w: 200 for w in weeks}}}
        now = datetime(2026, 10, 5, 12, tzinfo=timezone.utc)
        docs = {**self.DEFAULTS, "defaults": {"opus": "Opus 5.5", "sonnet": "Sonnet 5",
                                              "fable": "Fable 5.1"}}
        with_docs, _ = self._compute(defaults=docs, models=models, census=census, now=now)
        without, _ = self._compute(defaults=None, models=models, census=census, now=now)
        self.assertIn("claude-mythos-1", self._arms(with_docs))
        self.assertIn("carries", self._reason(with_docs, "claude-mythos-1"))
        self.assertEqual(with_docs["judge"]["id"], without["judge"]["id"])
        self.assertNotIn("claude-fable-5-1", self._arms(with_docs))
        self.assertIn("no `fable` model in it",
                      self._reason(with_docs, "claude-fable-5-1", "excluded"))
        for entry in with_docs["excluded"]:
            if entry["id"] == "claude-mythos-1":
                self.fail(entry["reason"])

    def test_the_committed_block_admits_one_default_per_family(self):
        base = yaml.safe_load((REPO_ROOT / "evals" / "roster.yml").read_text(encoding="utf-8"))
        block = {"source": DOCS_URL, "fetched_at": None,
                 "resolved": {"fable": "claude-fable-5-1", "mythos": "claude-mythos-1"}}
        self.assertEqual(roster.committed_roster_problems({**base, "defaults": block}), [])


class TestRound2Nits(_RosterFixture):
    """R2-5, R2-6, R2-7 (#203 round 2)."""

    def test_eval_yml_no_longer_says_a_failed_read_degrades_to_newest_in_tier(self):
        text = " ".join(EVAL_WORKFLOW.read_text(encoding="utf-8").split())
        for stale in ("a failed read degrades every tier to the newest-in-tier rule",
                      "roster.py falls back to newest-in-tier for every tier"):
            self.assertNotIn(stale, text)
        self.assertIn("carried in the committed roster", text)

    def _main_stderr(self, defaults_text, previous):
        tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
        (tmp / "models.json").write_text(json.dumps(self._models_doc()), encoding="utf-8")
        (tmp / "census.json").write_text(json.dumps(self._census()), encoding="utf-8")
        (tmp / "defaults.json").write_text(defaults_text, encoding="utf-8")
        (tmp / "previous.yml").write_text(yaml.safe_dump(previous), encoding="utf-8")
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
        err = io.StringIO()
        with mock.patch.object(sys, "argv", argv), \
             mock.patch.object(roster, "datetime", Frozen), \
             contextlib.redirect_stdout(io.StringIO()), \
             contextlib.redirect_stderr(err):
            rc = roster.main()
        self.assertEqual(rc, 0)
        return err.getvalue(), json.loads((tmp / "out.json").read_text(encoding="utf-8"))

    def test_an_unreadable_defaults_file_warns_once_with_the_carried_cause(self):
        previous = {**self.PREVIOUS, "defaults": TestCarriedDefaults.CARRIED}
        stderr, out = self._main_stderr("{not json", previous)
        lines = [ln for ln in stderr.splitlines() if "model defaults" in ln]
        self.assertEqual(len(lines), 1, stderr)
        self.assertIn("unreadable", lines[0])
        self.assertIn("carried", lines[0])
        self.assertNotIn("newest-in-tier", stderr)
        self.assertIs(out["defaults"]["carried"], True)

    def test_an_unreadable_defaults_file_with_no_carry_names_the_real_fallback(self):
        stderr, _ = self._main_stderr("{not json", self.PREVIOUS)
        lines = [ln for ln in stderr.splitlines() if "model defaults" in ln]
        self.assertEqual(len(lines), 1, stderr)
        self.assertIn("unreadable", lines[0])
        self.assertNotIn("every tier keeps the newest-in-tier rule", lines[0])

    def test_a_junk_source_publishes_the_docs_url(self):
        self.assertEqual(roster.DEFAULTS_DOCS_URL, fetch_model_defaults.DOCS_URL)
        result, _ = self._compute(defaults={**self.DEFAULTS,
                                            "source": "bad source with spaces"})
        self.assertEqual(result["defaults"]["source"], fetch_model_defaults.DOCS_URL)
        document = yaml.safe_load(render_roster_yaml.render(result, "1", "abc"))
        self.assertEqual(roster.committed_roster_problems(document), [])

    def test_a_committed_default_in_another_tier_is_rejected(self):
        base = yaml.safe_load((REPO_ROOT / "evals" / "roster.yml").read_text(encoding="utf-8"))
        block = {"source": DOCS_URL, "fetched_at": None,
                 "resolved": {"opus": "claude-haiku-4-5"}}
        problems = roster.committed_roster_problems({**base, "defaults": block})
        self.assertTrue(any("`defaults.resolved.opus`" in p and "tier" in p
                            for p in problems), problems)


class TestWorkflowIsLoudAboutCarriedDefaults(unittest.TestCase):
    """R2-1 (#203 round 2): the "Propose a roster change" step reads the
    carried flag from the computed latest.json at run time, emits a
    ::warning::, and keeps (or opens) the tracking issue on a `same` run."""

    START = "# >>> carried-defaults note"
    END = "# <<< carried-defaults note"

    def setUp(self):
        doc = yaml.safe_load(EVAL_WORKFLOW.read_text(encoding="utf-8"))
        self.run_block = next(s for s in doc["jobs"]["eval"]["steps"]
                              if s.get("name") == "Propose a roster change")["run"]

    def _fragment(self):
        self.assertIn(self.START, self.run_block)
        return self.run_block[self.run_block.index(self.START):
                              self.run_block.index(self.END)]

    def _run(self, latest):
        tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
        path = tmp / "latest.json"
        path.write_text(latest if isinstance(latest, str) else json.dumps(latest),
                        encoding="utf-8")
        script = (f"set -euo pipefail\ncomputed='{path}'\n" + self._fragment()
                  + '\nprintf "STATE=%s\\n" "$defaults_state"\n')
        done = subprocess.run(["bash", "-c", script], capture_output=True, text=True,
                              timeout=30, env={"PATH": os.environ.get("PATH", "")})
        self.assertEqual(done.returncode, 0, done.stderr)
        return done.stdout

    @unittest.skipUnless(shutil.which("bash"), "needs bash")
    def test_a_carried_roster_warns(self):
        out = self._run({"defaults": {"carried": True,
                                      "carried_reason": "HTTP 503 ::error::x"}})
        self.assertIn("STATE=carried", out)
        warning = [ln for ln in out.splitlines() if ln.startswith("::warning::")]
        self.assertEqual(len(warning), 1, out)
        self.assertNotIn("::error::", out)

    @unittest.skipUnless(shutil.which("bash"), "needs bash")
    def test_an_expired_carry_warns(self):
        out = self._run({"defaults": {"carried_expired": True, "resolved": {}}})
        self.assertIn("STATE=expired", out)
        self.assertEqual(len([ln for ln in out.splitlines()
                              if ln.startswith("::warning::")]), 1, out)

    @unittest.skipUnless(shutil.which("bash"), "needs bash")
    def test_a_healthy_or_junk_roster_is_quiet(self):
        for latest in ({"defaults": {"resolved": {"opus": "x"}}}, {},
                       {"defaults": {"carried": "true"}}, "[1, 2", "[]"):
            with self.subTest(latest=str(latest)[:30]):
                out = self._run(latest)
                self.assertIn("STATE=\n", out)
                self.assertNotIn("::warning::", out)

    def test_a_same_run_keeps_the_issue_when_carried(self):
        keep = self.run_block.index('if [ "$status" = "same" ] && [ -n "$defaults_state" ]; then')
        close = self.run_block.index("gh issue close")
        self.assertLess(self.run_block.index(self.END), keep)
        self.assertLess(keep, close)
        self.assertNotIn("${{", self._fragment())



if __name__ == "__main__":
    unittest.main()
