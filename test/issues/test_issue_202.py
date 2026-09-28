#!/usr/bin/env python3
"""Issue #202 — a tier's VENDOR-DEFAULT model takes its seat at once, and
the version it superseded retires after a buffer of complete ISO weeks
under the exit bar.

Three pieces, each tested here: `scripts/probe_model_defaults.py` (asks the
freshly installed Claude Code CLI, with no credential, which model each
family alias resolves to — #203), `harness/roster.py`'s
`defaults_doc`/`--defaults` (seats that default and retires what it
superseded), and `harness/timeweeks.py`'s complete-week helper the buffer is
counted with.

Hermetic, like the rest of the suite: the probe runs against
`test/fake-claude-init` (through a small wrapper that fixes its mode, because
the probe scrubs the environment it would otherwise be read from), never the
real CLI, and every roster call runs on a frozen `now`.

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
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
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
PROBE = SCRIPTS_DIR / "probe_model_defaults.py"
FAKE_CLAUDE_INIT = TEST_DIR / "fake-claude-init"
FAKE_VERSION_LINE = "fake-claude-init 0.0.0 (hermetic propagation stub)"

sys.path.insert(0, str(HARNESS_DIR))
import roster  # noqa: E402
import timeweeks  # noqa: E402

sys.path.insert(0, str(SCRIPTS_DIR))
import render_roster_yaml  # noqa: E402

#: The variables a scrubbed probe environment may carry. `LC_CTYPE` is not
#: the probe's: Python sets it itself at start-up when the locale is `C`
#: (PEP 538 coercion), and the wrapper that records the environment is Python.
#: The two switches the probe sets on purpose (#203 probe round 1, F5): no
#: auto-update, no nonessential traffic. Fixed values, never a credential —
#: and the only names allowed past `CREDENTIAL_NAME` below, by exact name.
PROBE_FLAGS = {"DISABLE_AUTOUPDATER": "1",
               "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC": "1"}
PROBE_ENV_ALLOWED = {"PATH", "HOME", "LANG", "XDG_CONFIG_HOME", "XDG_CACHE_HOME",
                     "XDG_DATA_HOME", "XDG_STATE_HOME", "LC_CTYPE", *PROBE_FLAGS}
CREDENTIAL_NAME = re.compile(r"^(ANTHROPIC_|CLAUDE_|AWS_|GOOGLE_)|TOKEN|KEY",
                             re.IGNORECASE)


def credential_like(names) -> list[str]:
    """Every credential-shaped name except the probe's own fixed flags."""
    return sorted(n for n in names if CREDENTIAL_NAME.search(n) and n not in PROBE_FLAGS)


class _ProbeFixture(unittest.TestCase):
    """Runs `scripts/probe_model_defaults.py` against the hermetic fake."""

    #: What the fake resolves the shipped ladder's aliases to.
    RESOLVED = {"haiku": "claude-haiku-4-5-20251001", "sonnet": "claude-sonnet-5",
                "opus": "claude-opus-5-5", "fable": "claude-fable-5-1"}

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)

    def _wrapper(self, mode="simulate", *, dump=None, version=None, extra_env=None):
        """A `claude` that records the environment it was given (one JSON
        line per call) and then runs the fake in `mode`. The mode cannot
        reach the fake through the environment: the probe scrubs it."""
        path = self.tmp / f"claude-{mode}"
        path.write_text(
            f"#!{sys.executable}\n"
            "import json, os, sys\n"
            f"dump = {str(dump) if dump else None!r}\n"
            "if dump:\n"
            "    home = os.environ.get('HOME', '')\n"
            "    record = {'env': dict(os.environ), 'cwd': os.getcwd(),\n"
            "              'home_is_dir': os.path.isdir(home),\n"
            "              'home_listing': sorted(os.listdir(home))\n"
            "              if os.path.isdir(home) else None}\n"
            "    with open(dump, 'a', encoding='utf-8') as f:\n"
            "        f.write(json.dumps(record) + '\\n')\n"
            f"if {version!r} is not None and '--version' in sys.argv:\n"
            f"    sys.stdout.write({version!r})\n"
            "    sys.exit(0)\n"
            f"os.environ['FAKE_INIT_MODE'] = {mode!r}\n"
            f"os.environ.update({dict(extra_env or {})!r})\n"
            f"os.execv(sys.executable, [sys.executable, {str(FAKE_CLAUDE_INIT)!r}]"
            " + sys.argv[1:])\n", encoding="utf-8")
        path.chmod(0o755)
        return path

    def _policy(self, tiers):
        path = self.tmp / "policy.yml"
        path.write_text(yaml.safe_dump({"tiers": tiers}), encoding="utf-8")
        return path

    def _probe(self, claude, *extra, env=None, timeout=120):
        out = self.tmp / "defaults.json"
        done = subprocess.run(
            [sys.executable, str(PROBE), "--claude", str(claude), "--out", str(out),
             *extra], capture_output=True, text=True, timeout=timeout,
            env=env if env is not None else dict(os.environ))
        document = (json.loads(out.read_text(encoding="utf-8"))
                    if out.is_file() else None)
        return done, document


class TestProbeScript(_ProbeFixture):
    """`scripts/probe_model_defaults.py` (#203): the vendor defaults come
    from the freshly installed CLI, probed with NO credential."""

    def test_the_shipped_ladder_resolves_four_and_skips_mythos(self):
        done, doc = self._probe(self._wrapper())
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertEqual(doc["defaults"], self.RESOLVED)
        self.assertEqual(doc["skipped"], ["mythos"])
        self.assertEqual(doc["errors"], {})
        self.assertEqual(doc["harness_version"], FAKE_VERSION_LINE)
        self.assertIsNotNone(timeweeks.parse_ts(doc["probed_at"]))
        self.assertEqual(set(doc), {"probed_at", "harness_version", "defaults",
                                    "skipped", "errors"})

    def test_the_aliases_come_from_the_policy_ladder(self):
        policy = self._policy(["haiku", ["opus", "zeta"]])
        done, doc = self._probe(self._wrapper(), "--policy", str(policy))
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertEqual(doc["defaults"], {"haiku": self.RESOLVED["haiku"],
                                           "opus": self.RESOLVED["opus"]})
        self.assertEqual(doc["skipped"], ["zeta"])

    def test_a_cli_that_exits_before_init_is_no_init(self):
        policy = self._policy(["opus", "sonnet"])
        for mode in ("crash", "no-init"):
            with self.subTest(mode=mode):
                done, doc = self._probe(self._wrapper(mode), "--policy", str(policy))
                self.assertEqual(done.returncode, 0, done.stderr)
                self.assertEqual(doc["defaults"], {})
                self.assertEqual(doc["errors"], {"opus": "no-init",
                                                  "sonnet": "no-init"})

    def test_a_cli_that_hangs_before_init_times_out(self):
        policy = self._policy(["opus"])
        done, doc = self._probe(self._wrapper("probe-hang"), "--policy", str(policy),
                                "--timeout", "0.5", timeout=60)
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertEqual(doc["errors"], {"opus": "timeout"})
        self.assertEqual(doc["defaults"], {})

    def test_a_junk_model_is_bad_model_and_never_echoed(self):
        policy = self._policy(["opus"])
        done, doc = self._probe(self._wrapper("junk-model"), "--policy", str(policy))
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertEqual(doc["errors"], {"opus": "bad-model"})
        self.assertEqual(doc["defaults"], {})
        for text in (done.stdout, done.stderr, json.dumps(doc)):
            self.assertNotIn("::error::", text)
            self.assertNotIn("Opus 5.5", text)

    def test_junk_lines_before_the_init_event_are_skipped(self):
        policy = self._policy(["opus"])
        done, doc = self._probe(self._wrapper("garbage-lines"), "--policy", str(policy))
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertEqual(doc["defaults"], {"opus": self.RESOLVED["opus"]})

    def test_the_cli_is_terminated_after_the_init_event(self):
        # The fake hangs for 600 s after init; a probe that waited for it
        # would blow this call's 60 s timeout long before its own 120 s one.
        policy = self._policy(["opus", "sonnet"])
        done, doc = self._probe(self._wrapper("init-then-hang"), "--policy",
                                str(policy), "--timeout", "120", timeout=60)
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertEqual(doc["defaults"], {"opus": self.RESOLVED["opus"],
                                           "sonnet": self.RESOLVED["sonnet"]})

    def test_a_cli_that_ignores_sigterm_is_killed(self):
        policy = self._policy(["opus"])
        done, doc = self._probe(self._wrapper("init-ignore-term"), "--policy",
                                str(policy), "--timeout", "120", timeout=60)
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertEqual(doc["defaults"], {"opus": self.RESOLVED["opus"]})

    def test_the_environment_is_scrubbed_and_home_is_a_fresh_temp_dir(self):
        dump = self.tmp / "env.jsonl"
        env = dict(os.environ, ANTHROPIC_API_KEY="k", ANTHROPIC_AUTH_TOKEN="t",
                   CLAUDE_CODE_OAUTH_TOKEN="t", AWS_SECRET_ACCESS_KEY="k",
                   GOOGLE_APPLICATION_CREDENTIALS="/x", GH_TOKEN="t",
                   SOME_API_KEY="k", HOME=str(self.tmp / "real-home"))
        policy = self._policy(["opus", "sonnet"])
        done, doc = self._probe(self._wrapper(dump=dump), "--policy", str(policy),
                                env=env)
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertEqual(len(doc["defaults"]), 2)
        records = [json.loads(line) for line in
                   dump.read_text(encoding="utf-8").splitlines()]
        # `--version` once, then one call per alias.
        self.assertEqual(len(records), 3)
        homes = set()
        for record in records:
            names = set(record["env"])
            self.assertLessEqual(names, PROBE_ENV_ALLOWED, names - PROBE_ENV_ALLOWED)
            self.assertEqual(credential_like(names), [])
            for flag, value in PROBE_FLAGS.items():
                self.assertEqual(record["env"].get(flag), value, flag)
            home = record["env"]["HOME"]
            self.assertNotEqual(home, env["HOME"])
            self.assertTrue(record["home_is_dir"])
            self.assertEqual(record["home_listing"],
                             sorted(p for p in record["home_listing"]
                                    if p in (".config", ".cache", ".local")))
            for key in ("XDG_CONFIG_HOME", "XDG_CACHE_HOME", "XDG_DATA_HOME",
                        "XDG_STATE_HOME"):
                self.assertTrue(record["env"][key].startswith(home + os.sep), key)
            self.assertEqual(record["env"]["LANG"], "C")
            self.assertEqual(record["cwd"], os.path.realpath(home))
            homes.add(home)
            # Removed afterwards.
            self.assertFalse(Path(home).exists(), home)
        self.assertEqual(len(homes), 3, "every CLI call gets its own fresh HOME")

    def test_scrubbed_env_keeps_nothing_from_the_parent(self):
        import probe_model_defaults
        parent = {"PATH": "/bin", "ANTHROPIC_API_KEY": "k", "CLAUDE_CONFIG_DIR": "/c",
                  "AWS_PROFILE": "p", "GOOGLE_CLOUD_PROJECT": "g", "MY_TOKEN": "t",
                  "DEPLOY_KEY": "k", "HOME": "/root", "USER": "u"}
        with mock.patch.dict(os.environ, parent, clear=True):
            env = probe_model_defaults.scrubbed_env(Path("/tmp/probe-home"))
        self.assertEqual(env["PATH"], "/bin")
        self.assertEqual(env["HOME"], "/tmp/probe-home")
        self.assertEqual(env["LANG"], "C")
        self.assertLessEqual(set(env), PROBE_ENV_ALLOWED - {"LC_CTYPE"})
        # F5 (#203 probe round 1): no auto-update, no nonessential traffic,
        # and still nothing credential-like past those two fixed flags.
        for flag, value in PROBE_FLAGS.items():
            self.assertEqual(env.get(flag), value, flag)
        self.assertEqual(credential_like(env), [])
        self.assertNotIn("/c", env.values())

    def test_a_missing_binary_is_a_usage_error(self):
        # F7 (#203 probe round 1): `--claude` is resolved once, up front; a
        # binary that is not there is the caller's mistake, said plainly,
        # and no document is written (eval.yml writes its own stand-in, so
        # the roster still freezes every family — see
        # TestWorkflowProbeFallbackDocument).
        missing = self.tmp / "no-such-claude"
        policy = self._policy(["opus", "sonnet"])
        done, doc = self._probe(missing, "--policy", str(policy))
        self.assertEqual(done.returncode, 2, done.stderr)
        self.assertIsNone(doc)
        self.assertIn("--claude", done.stderr)
        self.assertIn("no executable", done.stderr)

    def test_the_harness_version_is_sanitised_first_line(self):
        policy = self._policy(["opus"])
        done, doc = self._probe(self._wrapper(version="2.1.283 `(Claude Code)` ::x\n"
                                                      "second line\n"),
                                "--policy", str(policy))
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertEqual(doc["harness_version"], "2.1.283 (Claude Code) x")
        done, doc = self._probe(self._wrapper(version="`::`\n"), "--policy", str(policy))
        self.assertIsNone(doc["harness_version"])

    def test_an_unwritable_out_is_a_usage_error(self):
        blocker = self.tmp / "blocker"
        blocker.write_text("x", encoding="utf-8")
        done = subprocess.run(
            [sys.executable, str(PROBE), "--claude", str(self._wrapper()),
             "--policy", str(self._policy(["opus"])),
             "--out", str(blocker / "defaults.json")],
            capture_output=True, text=True, timeout=120)
        self.assertNotEqual(done.returncode, 0)

    def test_the_fetch_script_is_gone(self):
        self.assertFalse((SCRIPTS_DIR / "fetch_model_defaults.py").exists())


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


class TestDefaultsProvenance(unittest.TestCase):
    """Test _defaults_provenance function: it formats the source field and
    probed_at timestamp from a defaults document, stripping "(Claude Code)"
    suffix from the version if present."""

    def test_version_with_claude_code_suffix_is_stripped(self):
        """A version "2.1.283 (Claude Code)" should produce
        "claude-code-cli 2.1.283"."""
        source, probed_at = roster._defaults_provenance({
            "harness_version": "2.1.283 (Claude Code)",
            "probed_at": "2026-09-28T11:26:18Z"
        })
        self.assertEqual(source, "claude-code-cli 2.1.283")
        self.assertEqual(probed_at, "2026-09-28T11:26:18Z")

    def test_version_without_suffix_stays_the_same(self):
        """A version "2.1.283" without the suffix should still produce
        "claude-code-cli 2.1.283"."""
        source, probed_at = roster._defaults_provenance({
            "harness_version": "2.1.283",
            "probed_at": "2026-09-28T11:26:18Z"
        })
        self.assertEqual(source, "claude-code-cli 2.1.283")
        self.assertEqual(probed_at, "2026-09-28T11:26:18Z")

    def test_non_matching_version_gives_version_unknown(self):
        """A non-matching version value should give "claude-code-cli
        (version unknown)"."""
        source, probed_at = roster._defaults_provenance({
            "harness_version": None,
            "probed_at": "2026-09-28T11:26:18Z"
        })
        self.assertEqual(source, "claude-code-cli (version unknown)")
        self.assertEqual(probed_at, "2026-09-28T11:26:18Z")

    def test_claude_code_suffix_is_case_sensitive(self):
        """Only exact " (Claude Code)" suffix (case-sensitive) is stripped."""
        source, probed_at = roster._defaults_provenance({
            "harness_version": "2.1.283 (claude code)",
            "probed_at": "2026-09-28T11:26:18Z"
        })
        # Since the version matches the regex, it should be used as-is.
        # The lowercase version does NOT match the suffix pattern.
        self.assertEqual(source, "claude-code-cli 2.1.283 (claude code)")


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

    #: `scripts/probe_model_defaults.py`'s document (#203): model ids, read
    #: off the unauthenticated CLI's init event.
    DEFAULTS = {"probed_at": "2026-09-27T10:00:00Z",
                "harness_version": "2.1.283 (Claude Code)",
                "defaults": {"opus": "claude-opus-5-5", "sonnet": "claude-sonnet-5"},
                "skipped": ["mythos"], "errors": {}}
    #: What the published block and every reason name as the source.
    SOURCE = "claude-code-cli 2.1.283"

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
        self.assertIn(self.SOURCE, new)
        self.assertIn("probed 2026-09-27T10:00:00Z", new)
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
        self.assertEqual(result["defaults"]["source"], self.SOURCE)
        self.assertEqual(result["defaults"]["probed_at"], "2026-09-27T10:00:00Z")
        self.assertEqual(set(result["defaults"]),
                         {"source", "probed_at", "resolved", "unresolved"})
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
        defaults = {**self.DEFAULTS, "defaults": {"opus": "claude-opus-5",
                                                  "sonnet": "claude-sonnet-5"}}
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
        defaults = {**self.DEFAULTS, "defaults": {"opus": "claude-opus-5-5",
                                                  "sonnet": "claude-sonnet-5",
                                                  "fable": "claude-fable-5-1"}}
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
                                                  "haiku": "claude-haiku-5"}}
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
        self.assertIn(self.SOURCE, summary)
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


class _PreviewFixture(_RosterFixture):
    """A catalogue with a model newer than the opus default (`opus-5-6`)."""

    WEEKS = [f"2026-W{n:02d}" for n in range(33, 42)]
    NOW_OCT = datetime(2026, 10, 12, 12, tzinfo=timezone.utc)
    D = {**_RosterFixture.DEFAULTS, "defaults": {"opus": "claude-opus-5-5",
                                                 "sonnet": "claude-sonnet-5"}}
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


class TestPreviewArmGetsTheExitCheck(_PreviewFixture):
    """F2(b) (#203 round 1): a previous arm NEWER than its tier's default is
    no longer retired on sight — it gets rule 3's exit check. It still
    earns no NEW seat."""

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


class TestNoCarriedDefaults(_RosterFixture):
    """#203: the carried-defaults machinery is gone — the owner's decision:
    nothing is carried from one run to the next. The committed roster keeps
    no `defaults:` block, and a block an older committed roster still has is
    never read. A failed probe FREEZES its families for that one run
    (#203 probe round 1; see TestFailedProbeFreezesItsFamily), which is not
    a carry: nothing about the failure outlives the run."""

    OLD_BLOCK = {"source": "https://code.claude.com/docs/en/model-config.md",
                 "fetched_at": "2026-09-27T10:00:00Z",
                 "resolved": {"opus": "claude-opus-5-5", "sonnet": "claude-sonnet-5"}}
    DOWN = {"probed_at": "2026-09-27T10:00:00Z", "harness_version": None,
            "defaults": {}, "skipped": [],
            "errors": {"haiku": "no-init", "sonnet": "no-init", "opus": "no-init",
                       "fable": "no-init", "mythos": "no-init"}}

    def test_a_failed_probe_never_reads_a_committed_defaults_block(self):
        with_block = {**self.PREVIOUS, "defaults": copy.deepcopy(self.OLD_BLOCK)}
        # No document at all: byte for byte the roster without one.
        baseline, _ = self._compute()
        result, _ = self._compute(defaults=None, previous=with_block)
        self.assertEqual(json.dumps(result, sort_keys=True),
                         json.dumps(baseline, sort_keys=True))
        # A failed probe: frozen, and the old block still decides nothing —
        # the same roster the same failure computes without the block.
        failed, _ = self._compute(defaults=self.DOWN)
        result, _ = self._compute(defaults=self.DOWN, previous=with_block)
        self.assertNotIn("defaults", result)
        self.assertNotIn("vendor default for the", json.dumps(result))
        self.assertNotIn("claude-opus-5-5", self._arms(result))
        self.assertEqual(json.dumps(result, sort_keys=True),
                         json.dumps(failed, sort_keys=True))

    def test_the_rendered_roster_has_no_defaults_block(self):
        result, _ = self._compute(defaults=self.DEFAULTS)
        self.assertIn("defaults", result)
        text = render_roster_yaml.render(result, "1", "abc")
        document = yaml.safe_load(text)
        self.assertNotIn("defaults", document)
        self.assertNotIn("defaults:", text)
        self.assertEqual(roster.committed_roster_problems(document), [])

    def test_the_published_roster_keeps_the_block_for_the_reviewer(self):
        result, _ = self._compute(defaults=self.DEFAULTS)
        self.assertEqual(result["defaults"], {
            "source": self.SOURCE, "probed_at": "2026-09-27T10:00:00Z",
            "resolved": {"opus": "claude-opus-5-5", "sonnet": "claude-sonnet-5"},
            "unresolved": []})

    def test_no_change_kind_is_about_defaults(self):
        prev = {**self.PREVIOUS, "arms": [{"id": "claude-sonnet-5"},
                                          {"id": "claude-opus-5-5"}],
                "defaults": copy.deepcopy(self.OLD_BLOCK)}
        census = self._later_census(opus5_w40=5, opus55_w40=440)
        for doc in (self.DEFAULTS, self.DOWN):
            with self.subTest(doc=bool(doc["defaults"])):
                result, _ = self._compute(defaults=doc, previous=prev,
                                          census=census, now=self.LATER)
                self.assertEqual([c for c in result["proposal"]["changes"]
                                  if c["kind"] == "defaults"
                                  or c["field"].startswith("defaults")], [])

    def test_no_doc_renders_no_defaults_block(self):
        result, _ = self._compute()
        self.assertNotIn("defaults:", render_roster_yaml.render(result, "1", "abc"))

    def test_the_carry_machinery_is_gone(self):
        for name in ("_carried_defaults", "_drop_stale_carried",
                     "_committed_defaults_problems", "COMMITTED_DEFAULTS_KEYS",
                     "DEFAULTS_DOCS_URL", "DEFAULTS_NAME_RE"):
            self.assertFalse(hasattr(roster, name), name)
        self.assertFalse(hasattr(render_roster_yaml, "_defaults_lines"))
        self.assertNotIn("carried", roster.render_summary(
            self._compute(defaults=self.DEFAULTS)[0]))


class TestUnresolvedDefaultsFallBack(_RosterFixture):
    """A PROBE FAILURE — an error recorded for the alias, or a document that
    resolved nothing — FREEZES that family for the run (#203 probe round 1):
    its previous arms are held, nothing of it is newly seated but by usage,
    and a warning says so. A CATALOGUE MISMATCH — the probe answered, but
    this run's catalogue does not match the answer — freezes too, exactly
    the same way, in its own wording (#203 probe round 2, R2-1; round 7,
    R7-1)."""

    @staticmethod
    def _policy(**overrides):
        # A POSITIVE cooling-off, supplied rather than read: the shipped
        # value is 0 since the owner's decision of 2026-09-27 (#202), and
        # these tests pin that an unresolved default leaves its tier on the
        # rule that applies the cooling-off whenever one is configured.
        return _RosterFixture._policy(**{"cooling_off_days": 7, **overrides})

    def _assert_todays_opus_rule(self, result):
        # opus-5 is a previous arm: held by the freeze, not by usage.
        # opus-5-5 gets no new seat, and the freeze — not the cooling-off —
        # is the reason given.
        self.assertIn("claude-opus-5", self._arms(result))
        self.assertIn("vendor default for `opus` unknown this run",
                      self._reason(result, "claude-opus-5"))
        self.assertNotIn("claude-opus-5-5", self._arms(result))
        self.assertIn("vendor default for `opus` unknown this run",
                      self._reason(result, "claude-opus-5-5", "excluded"))
        self.assertIn("opus", result["defaults_failed"])
        if "defaults" in result:
            self.assertNotIn("opus", result["defaults"]["resolved"])

    def _assert_opus_frozen_on_a_mismatch(self, result, cls):
        # A catalogue mismatch (R2-1) freezes exactly like a probe failure
        # (R7-1, #203 probe round 7): opus-5, a listed previous arm, is
        # held; opus-5-5 gets no new seat while it holds that seat.
        self.assertNotIn("defaults_failed", result)
        self.assertEqual(result["defaults_mismatched"]["opus"]["class"], cls)
        self.assertIn("claude-opus-5", self._arms(result))
        self.assertIn("held; none retired on a catalogue mismatch",
                      self._reason(result, "claude-opus-5"))
        self.assertNotIn("claude-opus-5-5", self._arms(result))
        self.assertIn("no new seat on a catalogue mismatch while the family "
                      "holds a seat the Models API still lists",
                      self._reason(result, "claude-opus-5-5", "excluded"))

    def test_an_id_that_is_not_available(self):
        defaults = {**self.DEFAULTS, "defaults": {"opus": "claude-opus-9",
                                                  "sonnet": "claude-sonnet-5"}}
        result, warnings = self._compute(defaults=defaults)
        self._assert_opus_frozen_on_a_mismatch(result, "not-available")
        self.assertTrue(any("`opus`" in w and "not an available model" in w
                            for w in warnings), warnings)
        self.assertEqual(result["defaults"]["unresolved"][0]["alias"], "opus")
        self.assertIn("claude-opus-9", result["defaults"]["unresolved"][0]["reason"])

    def test_an_id_in_the_wrong_tier(self):
        # R3-2 (#203 probe round 3): a wrong-tier answer is nonsensical, so
        # it is a probe FAILURE and freezes, not a catalogue mismatch.
        defaults = {**self.DEFAULTS, "defaults": {"opus": "claude-sonnet-5",
                                                  "sonnet": "claude-sonnet-5"}}
        result, warnings = self._compute(defaults=defaults)
        self._assert_todays_opus_rule(result)
        self.assertEqual(result["defaults_failed"], {"opus": "wrong-tier"})
        self.assertNotIn("defaults_mismatched", result)
        self.assertTrue(any("`opus`" in w and "sonnet tier" in w and "nonsensical" in w
                            for w in warnings), warnings)

    def test_an_alias_off_the_ladder_is_ignored(self):
        defaults = {**self.DEFAULTS, "defaults": {"opusplan": "claude-opus-5-5"}}
        result, warnings = self._compute(defaults=defaults)
        self._assert_todays_opus_rule(result)
        self.assertTrue(any("not a family word" in w for w in warnings), warnings)

    def test_a_probe_error_leaves_that_alias_unresolved_with_its_class(self):
        defaults = {**self.DEFAULTS, "defaults": {"sonnet": "claude-sonnet-5"},
                    "errors": {"opus": "timeout", "haiku": "::error::x\ny"}}
        result, warnings = self._compute(defaults=defaults)
        self._assert_todays_opus_rule(result)
        self.assertEqual(result["defaults"]["resolved"], {"sonnet": "claude-sonnet-5"})
        reasons = {u["alias"]: u["reason"] for u in result["defaults"]["unresolved"]}
        self.assertIn("timeout", reasons["opus"])
        self.assertIn("an error was recorded", reasons["haiku"])
        self.assertTrue(any("`opus`" in w and "timeout" in w for w in warnings), warnings)
        self.assertNotIn("::error::", json.dumps(result) + "\n".join(warnings))

    def test_a_skipped_alias_is_not_unresolved(self):
        result, warnings = self._compute(defaults=self.DEFAULTS)
        self.assertNotIn("mythos", [u["alias"] for u in result["defaults"]["unresolved"]])
        self.assertFalse(any("mythos" in w for w in warnings), warnings)

    def test_junk_is_ignored_with_a_warning(self):
        for junk in ({"defaults": ["opus"]},
                     {"defaults": {"opus": 5}},
                     {"defaults": {"opus": "x" * 65}},
                     {"defaults": {"opus": "Opus 5.5"}},
                     {"defaults": {"opus": "claude-opus-5-5\n::error::x"}},
                     {"defaults": {"OPUS": "claude-opus-5-5"}},
                     {"defaults": {f"a{i}": "claude-opus-5-5" for i in range(17)}}):
            with self.subTest(junk=str(junk)[:40]):
                doc = {**self.DEFAULTS, **junk}
                result, warnings = self._compute(defaults=doc)
                self.assertNotIn("claude-opus-5-5", self._arms(result))
                self.assertTrue(warnings)
                self.assertFalse(any("::error::" in w for w in warnings), warnings)
                self.assertNotIn("::error::", json.dumps(result))


class TestSnapshotDefaults(_RosterFixture):
    """#203: the CLI can resolve an alias to a DATED id (haiku did, on
    2.1.283). Where the catalogue also lists the undated alias the roster
    collapses the snapshot onto it, and the default resolves to that seat."""

    def test_a_dated_default_resolves_onto_its_undated_alias(self):
        models = self._models_doc(extra=[self._model(
            "claude-haiku-4-5-20251001", "Claude Haiku 4.5", "2025-10-01T00:00:00Z")])
        defaults = {**self.DEFAULTS, "defaults": {**self.DEFAULTS["defaults"],
                                                  "haiku": "claude-haiku-4-5-20251001"}}
        result, warnings = self._compute(defaults=defaults, models=models)
        self.assertEqual(result["defaults"]["resolved"]["haiku"], "claude-haiku-4-5")
        self.assertEqual(result["defaults"]["unresolved"], [])
        self.assertFalse(any("haiku" in w for w in warnings), warnings)

    def test_a_dated_default_alone_in_the_catalogue_stands_on_its_own(self):
        models = self._models_doc(
            extra=[self._model("claude-haiku-4-5-20251001", "Claude Haiku 4.5",
                               "2025-10-01T00:00:00Z")],
            drop=("claude-haiku-4-5",))
        defaults = {**self.DEFAULTS, "defaults": {"haiku": "claude-haiku-4-5-20251001"}}
        result, _ = self._compute(defaults=defaults, models=models)
        self.assertEqual(result["defaults"]["resolved"],
                         {"haiku": "claude-haiku-4-5-20251001"})


class TestAliasConflicts(_RosterFixture):
    """F7 (#203 round 1), revised by R2-4 (#203 round 2): an alias resolves
    only to a model of its OWN family word. Two peer aliases in one rung
    (`fable`, `mythos`) are two families, not a conflict; a peer alias
    naming another family's model is unresolved on its own."""

    def test_a_peer_alias_naming_another_family_is_unresolved_alone(self):
        defaults = {**self.DEFAULTS, "defaults": {"fable": "claude-fable-5-1",
                                                  "mythos": "claude-fable-5"}}
        result, warnings = self._compute(defaults=defaults)
        self.assertEqual(result["defaults"]["resolved"], {"fable": "claude-fable-5-1"})
        self.assertEqual([u["alias"] for u in result["defaults"]["unresolved"]],
                         ["mythos"])
        self.assertTrue(any("`mythos`" in w and "fable family" in w
                            for w in warnings), warnings)

    def test_peer_aliases_naming_their_own_families_both_resolve(self):
        models = self._models_doc(extra=[self._model(
            "claude-mythos-1", "Claude Mythos 1", "2026-09-20T00:00:00Z")])
        defaults = {**self.DEFAULTS, "defaults": {"fable": "claude-fable-5-1",
                                                  "mythos": "claude-mythos-1"}}
        result, _ = self._compute(defaults=defaults, models=models)
        self.assertEqual(result["defaults"]["resolved"],
                         {"fable": "claude-fable-5-1", "mythos": "claude-mythos-1"})
        self.assertEqual(result["defaults"]["unresolved"], [])

    def test_a_third_peer_off_its_family_does_not_block_the_others(self):
        policy = self._policy(tiers=["haiku", "sonnet", "opus",
                                     ["fable", "mythos", "fablex"]])
        defaults = {**self.DEFAULTS, "defaults": {"fable": "claude-fable-5-1",
                                                  "mythos": "claude-fable-5",
                                                  "fablex": "claude-fable-5-1"}}
        result, _ = self._compute(defaults=defaults, policy=policy)
        self.assertEqual(result["defaults"]["resolved"], {"fable": "claude-fable-5-1"})
        self.assertEqual(sorted(u["alias"] for u in result["defaults"]["unresolved"]),
                         ["fablex", "mythos"])


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
    """No probe document at all is the same roster the pre-#202 code
    computes, with one exception (N1, #203 adversarial round 10):
    `_seated_form`'s recognition of a previous arm whose listed spelling
    switched between dated and undated is not gated on a defaults document
    existing, so a renamed previous arm is still held under its new
    spelling rather than reading as "no longer returned" and dropping its
    seat outright — see TestNoDocumentStillRecognizesARename. A document
    that failed entirely is NOT unchanged (#203 probe round 1): it freezes
    every family it could not vouch for — see
    TestFailedProbeFreezesItsFamily."""

    FAILED = {"probed_at": "2026-09-27T10:00:00Z", "harness_version": None,
              "defaults": {}, "skipped": [],
              "errors": {"haiku": "timeout", "sonnet": "timeout",
                         "opus": "timeout", "fable": "timeout", "mythos": "timeout"}}

    def test_no_doc_changes_nothing(self):
        baseline, _ = self._compute()
        result, warnings = self._compute(defaults=None)
        self.assertEqual(json.dumps(result, sort_keys=True),
                         json.dumps(baseline, sort_keys=True))
        self.assertNotIn("defaults_failed", result)
        self.assertEqual(warnings, [])

    def test_empty_and_failed_docs_freeze_rather_than_change_nothing(self):
        baseline, _ = self._compute()
        # Without a document, the usage rules seat opus-5-5 as newest in a
        # qualifying tier; every failed document must hold the opus tier
        # where it stands instead.
        self.assertIn("claude-opus-5-5", self._arms(baseline))
        for doc in ({}, self.FAILED,
                    {**self.DEFAULTS, "defaults": {}},
                    {**self.FAILED, "errors": {"opus": "FileNotFoundError"}},
                    {**self.DEFAULTS, "defaults": None},
                    "not a mapping"):
            with self.subTest(doc=str(doc)[:40]):
                result, _ = self._compute(defaults=doc)
                self.assertEqual(sorted(self._arms(result)),
                                 ["claude-opus-5", "claude-sonnet-5"])
                self.assertIn("opus", result["defaults_failed"])
                self.assertIn("sonnet", result["defaults_failed"])
                self.assertEqual(result["retired_since_last"], [])

    def test_a_failed_probe_says_so_in_one_warning(self):
        _, warnings = self._compute(defaults=self.FAILED)
        said = [w for w in warnings if "model defaults" in w]
        self.assertEqual(len(said), 1, warnings)
        self.assertIn("timeout", said[0])
        self.assertIn("held", said[0])
        self.assertIn("none retired except models gone from the Models API", said[0])
        self.assertIn("none added unless the family holds no seat the Models API "
                      "still lists", said[0])
        self.assertNotIn("usage and newest-in-tier rules", said[0])


class TestNoDocumentStillRecognizesARename(_RosterFixture):
    """N1 (#203 adversarial round 10): with NO defaults document at all,
    a previous arm whose listed spelling switched between dated and
    undated since the previous run is still recognized as that arm — the
    one way the no-document roster is NOT byte-for-byte the pre-#202
    code's, which just read the dated spelling as gone and dropped the
    seat. The reviewer's nodoc.py ("dated->alias only")."""

    def test_a_dated_previous_arm_collapses_onto_its_now_listed_alias(self):
        previous = {**self.PREVIOUS, "arms": [{"id": "claude-sonnet-5"},
                                              {"id": "claude-opus-5-20260401"}]}
        result, _ = self._compute(defaults=None, previous=previous)
        self.assertIn("claude-opus-5", self._arms(result))
        why = self._reason(result, "claude-opus-5-20260401", "retired_since_last")
        self.assertIn("collapsed onto its undated alias `claude-opus-5`", why)
        self.assertIn("which holds the seat", why)


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


class TestWorkflowProbesDefaults(unittest.TestCase):
    """eval.yml's roster step probes the installed CLI (#203) before the
    Models API bearer is exported, and the probe cannot fail the step."""

    def _roster_step(self):
        doc = yaml.safe_load(EVAL_WORKFLOW.read_text(encoding="utf-8"))
        return next(s for s in doc["jobs"]["eval"]["steps"]
                    if "roster" in (s.get("name") or "").lower())["run"]

    def test_the_roster_step_probes_defaults_first_and_passes_them(self):
        script = self._roster_step()
        self.assertNotIn("fetch_model_defaults", script)
        probe_at = script.index("scripts/probe_model_defaults.py")
        roster_at = script.index("harness/roster.py")
        self.assertLess(probe_at, roster_at)
        self.assertIn('--out "$work/defaults.json"', script[probe_at:roster_at])
        self.assertIn('--defaults "$work/defaults.json"', script[roster_at:])
        self.assertNotIn("${{", script)

    def test_the_probe_runs_before_the_bearer_is_exported(self):
        lines = [ln.strip() for ln in self._roster_step().splitlines()]
        probe = next(i for i, ln in enumerate(lines)
                     if "scripts/probe_model_defaults.py" in ln
                     and not ln.startswith("#"))
        bearer = [i for i, ln in enumerate(lines)
                  if "ANTHROPIC_AUTH_TOKEN" in ln and not ln.startswith("#")]
        self.assertTrue(bearer)
        self.assertLess(probe, min(bearer))

    def test_the_probe_cannot_fail_the_step(self):
        script = self._roster_step()
        line = next(ln for ln in script.splitlines()
                    if "scripts/probe_model_defaults.py" in ln
                    and not ln.strip().startswith("#"))
        self.assertTrue(line.rstrip().endswith("|| true"), line)

    def test_the_probe_scrubs_the_environment_regardless(self):
        # Order in the step is one guard; this is the other. Even with the
        # bearer (and every other credential shape) in the parent process,
        # the CLI it starts sees none of it.
        import probe_model_defaults
        parent = {"PATH": "/usr/bin", "ANTHROPIC_AUTH_TOKEN": "bearer",
                  "ANTHROPIC_API_KEY": "k", "ANTHROPIC_ADMIN_KEY": "k",
                  "GITHUB_TOKEN": "t", "ACTIONS_ID_TOKEN_REQUEST_TOKEN": "t",
                  "ACTIONS_RUNTIME_TOKEN": "t", "CLAUDE_CODE_USE_BEDROCK": "1"}
        with mock.patch.dict(os.environ, parent, clear=True):
            env = probe_model_defaults.scrubbed_env(Path("/tmp/probe-home"))
        self.assertEqual(credential_like(env), [])
        self.assertNotIn("bearer", json.dumps(env))
        self.assertNotIn("CLAUDE_CODE_USE_BEDROCK", env)


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
                                   "GITHUB_EVENT_PATH": str(tmp / "event.json"),
                                   # A normal run's eval step succeeded (#203
                                   # probe round 3 reads its outcome).
                                   "EVAL_OUTCOME": "success"})
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

    @staticmethod
    def _week_number(label):
        year, week = label.split("-W")
        return (int(year) - 2026) * 53 + int(week)

    def _docs(self, k, **defaults):
        probed = (self.START + timedelta(weeks=k, hours=11)).strftime("%Y-%m-%dT%H:%M:%SZ")
        return {"probed_at": probed, "harness_version": "2.1.283 (Claude Code)",
                "defaults": defaults or {"opus": "claude-opus-5-5",
                                         "sonnet": "claude-sonnet-5"},
                "skipped": ["mythos"], "errors": {}}

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


class TestNoCarryPolicyKey(unittest.TestCase):
    """#203: `defaults_carry_max_age_days` went with the carry."""

    def test_the_shipped_policy_has_no_carry_key_and_validates(self):
        policy = roster.load_policy(POLICY)
        self.assertNotIn("defaults_carry_max_age_days", policy)
        roster.validate_policy(policy)
        self.assertNotIn("defaults_carry_max_age_days", POLICY.read_text(encoding="utf-8"))

    def test_the_eval_workflow_has_no_carried_defaults_note(self):
        text = EVAL_WORKFLOW.read_text(encoding="utf-8")
        for stale in ("carried-defaults note", "defaults_state", "carried_note",
                      "defaults_carry_max_age_days", "vendor defaults carried"):
            self.assertNotIn(stale, text)


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
        docs = {**self.DEFAULTS, "defaults": {"opus": "claude-opus-5-5",
                                              "sonnet": "claude-sonnet-5",
                                              "fable": "claude-fable-5-1"}}
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


class TestRound2Nits(_RosterFixture):
    """R2-5 and R2-6 (#203 round 2), as they stand after the probe."""

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

    def test_an_unreadable_defaults_file_warns_once_and_names_the_real_fallback(self):
        for previous in (self.PREVIOUS,
                         {**self.PREVIOUS, "defaults": TestNoCarriedDefaults.OLD_BLOCK}):
            with self.subTest(block="defaults" in previous):
                stderr, out = self._main_stderr("{not json", previous)
                lines = [ln for ln in stderr.splitlines() if "model defaults" in ln]
                self.assertEqual(len(lines), 1, stderr)
                self.assertIn("unreadable", lines[0])
                # R2-1(c), R3-4(c): held, none retired but a model gone
                # from the Models API.
                self.assertIn("none retired except models gone from the Models API",
                              lines[0])
                self.assertNotIn("carried", stderr)
                self.assertNotIn("defaults", out)
                # F1/F3 (#203 probe round 1): unreadable freezes every
                # family on the ladder, and the published roster says so.
                self.assertEqual(out["defaults_document_failed"], "unreadable")
                self.assertEqual(set(out["defaults_failed"]),
                                 set(roster.tier_words(self._policy())))

    def test_a_junk_harness_version_publishes_an_unknown_version(self):
        for junk in ("bad ::error:: `version`", 5, None, "x" * 200):
            with self.subTest(junk=str(junk)[:20]):
                result, _ = self._compute(defaults={**self.DEFAULTS,
                                                    "harness_version": junk})
                self.assertEqual(result["defaults"]["source"],
                                 "claude-code-cli (version unknown)")
                self.assertNotIn("::", json.dumps(result["defaults"]))

    def test_a_junk_probed_at_publishes_null(self):
        result, _ = self._compute(defaults={**self.DEFAULTS, "probed_at": "yesterday"})
        self.assertIsNone(result["defaults"]["probed_at"])
        self.assertIn("probed at an unknown time", self._reason(result, "claude-opus-5-5"))



# --- #203 probe round 1 -------------------------------------------------------


def _s5_usage(n):
    """The reviewer's S5 fleet: the opus tier at a steady ~5% (between the
    2% exit and 10% entry bars), switching from 5 to 5.5 in W40."""
    return {"claude-sonnet-5": 900, "claude-haiku-4-5": 50, "claude-fable-5-1": 0,
            "claude-opus-5": 0 if n >= 40 else 50,
            "claude-opus-5-5": 50 if n >= 40 else 0}


class TestFailedProbeFreezesItsFamily(_WeeklyLoop):
    """F1 + F2 (#203 probe round 1): a family whose vendor default the probe
    could not establish is FROZEN for that run — its previous arms keep
    their seats, none of its models is newly seated, none is retired. Per
    run only: nothing is carried to the next (the owner's decision)."""

    HELD = ("vendor default for `opus` unknown this run (probe: timeout); held; "
            "none retired on a failed probe")

    def _failing(self, weeks, errors, defaults=None):
        def docs(k):
            doc = self._docs(k)
            if k in weeks:
                doc["defaults"] = dict(defaults or {})
                doc["errors"] = dict(errors)
            return doc
        return docs

    def test_flip_a_one_week_opus_failure_changes_no_opus_seat(self):
        # The reviewer's flip.py: week 2's opus probe times out. Without the
        # freeze the tier fell back to the usage rules, retired the seated
        # default that week, and never seated it again.
        out, _ = self._loop(_s5_usage, 6, self._failing(
            {2}, {"opus": "timeout"}, {"sonnet": "claude-sonnet-5"}))
        self.assertEqual(out[2]["result"]["retired_since_last"], [])
        self.assertEqual(out[2]["result"]["added_since_last"], [])
        week1 = self._arms(out[1]["result"])
        self.assertIn("claude-opus-5-5", week1)
        for k in range(2, 6):
            self.assertEqual(self._arms(out[k]["result"]), week1, k)
        self.assertEqual(self._reason(out[2]["result"], "claude-opus-5-5"), self.HELD)
        self.assertEqual(out[2]["result"]["defaults_failed"], {"opus": "timeout"})
        # The next week probes cleanly and decides as usual: nothing carried.
        self.assertNotIn("defaults_failed", out[3]["result"])
        self.assertIn("vendor default for the opus tier",
                      self._reason(out[3]["result"], "claude-opus-5-5"))

    def test_total_every_alias_failing_holds_every_previous_arm(self):
        # The reviewer's total.py: every alias fails in week 2.
        errors = {a: "no-init" for a in ("opus", "sonnet", "haiku", "fable")}
        out, _ = self._loop(_s5_usage, 3, self._failing({2}, errors))
        week2 = out[2]["result"]
        self.assertEqual(week2["retired_since_last"], [])
        self.assertEqual(week2["added_since_last"], [])
        self.assertEqual(self._arms(week2), self._arms(out[1]["result"]))
        self.assertEqual(week2["defaults_failed"], errors)
        self.assertEqual(week2["defaults_document_failed"], "no-defaults")
        for arm in week2["arms"]:
            self.assertIn("unknown this run (probe: no-init)", arm["reason"])
        # Nothing of a frozen family is newly seated: haiku and fable say why.
        for model_id in ("claude-haiku-4-5", "claude-fable-5-1"):
            self.assertIn("no new seat on a failed probe",
                          self._reason(week2, model_id, "excluded"))
        self.assertEqual(week2["proposal"]["status"], "same")

    def test_a_skipped_family_is_not_frozen(self):
        # mythos is `skipped` (not an alias of this CLI), so it was never a
        # default to fail: a new mythos model is seated by the usage rules
        # exactly as without a document.
        models = list(self.BASE) + [self._model(
            "claude-mythos-1", "Claude Mythos 1", "2026-09-20T00:00:00Z")]

        def usage(n):
            return {**_s5_usage(n), "claude-mythos-1": 400}

        errors = {a: "no-init" for a in ("opus", "sonnet", "haiku", "fable")}
        out, _ = self._loop(usage, 1, self._failing({0}, errors), models=models)
        result = out[0]["result"]
        self.assertIn("claude-mythos-1", self._arms(result))
        self.assertIn("carries", self._reason(result, "claude-mythos-1"))
        self.assertNotIn("mythos", result["defaults_failed"])
        # Recorded as an error instead, mythos is frozen like the rest — and
        # a frozen family holding no listed seat still seats a model that
        # clears the usage entry bar (R2-1(c), #203 probe round 2; R3-1).
        out, _ = self._loop(usage, 1, self._failing(
            {0}, {**errors, "mythos": "no-init"}), models=models)
        self.assertIn("mythos", out[0]["result"]["defaults_failed"])
        self.assertIn("unknown this run (probe: no-init), and the family holds no "
                      "seat the Models API still lists, so this seat rests on usage "
                      "alone", self._reason(out[0]["result"], "claude-mythos-1"))

    def test_an_unreadable_document_freezes_every_family(self):
        warnings: list[str] = []
        result = roster.compute_roster(
            models_doc=self._models_doc(), census_doc=self._census(),
            policy=self._policy(), previous=copy.deepcopy(self.PREVIOUS),
            now=self.NOW, warn=warnings.append, defaults_doc=None,
            defaults_problem="defaults.json is present but unreadable (ValueError)")
        self.assertEqual(result["defaults_document_failed"], "unreadable")
        self.assertEqual(result["defaults_failed"],
                         {w: "unreadable" for w in roster.tier_words(self._policy())})
        self.assertEqual(sorted(self._arms(result)), ["claude-opus-5", "claude-sonnet-5"])
        self.assertEqual(result["retired_since_last"], [])

    def test_a_frozen_family_retires_nothing_even_under_the_exit_bar(self):
        # A previous opus arm at 0% for eight weeks would retire by rule 3;
        # frozen, it is held.
        weeks = [f"2026-W{n:02d}" for n in range(36, 50)]
        census = {"generated_at": "2026-12-07T06:00:00Z", "weeks": [], "counts": {
            "claude-sonnet-5": {w: 900 for w in weeks},
            "claude-haiku-4-5": {w: 100 for w in weeks}}}
        previous = {**self.PREVIOUS, "arms": [{"id": "claude-sonnet-5"},
                                              {"id": "claude-opus-5-5"}]}
        doc = {**self.DEFAULTS, "defaults": {"sonnet": "claude-sonnet-5"},
               "errors": {"opus": "timeout"}}
        result, _ = self._compute(defaults=doc, previous=previous, census=census,
                                  now=datetime(2026, 12, 8, 12, tzinfo=timezone.utc))
        self.assertIn("claude-opus-5-5", self._arms(result))
        self.assertEqual(result["retired_since_last"], [])
        self.assertEqual(self._reason(result, "claude-opus-5-5"), self.HELD)

    def test_a_frozen_family_keeps_a_snapshot_arm_on_its_collapsed_alias(self):
        # A previous arm published under a dated id whose undated alias the
        # catalogue now lists is the same seat, renamed — not a new one.
        models = self._models_doc(extra=[self._model(
            "claude-opus-5-20260401", "Claude Opus 5", "2026-04-01T00:00:00Z")])
        previous = {**self.PREVIOUS, "arms": [{"id": "claude-sonnet-5"},
                                              {"id": "claude-opus-5-20260401"}]}
        doc = {**self.DEFAULTS, "defaults": {"sonnet": "claude-sonnet-5"},
               "errors": {"opus": "timeout"}}
        result, _ = self._compute(defaults=doc, previous=previous, models=models)
        self.assertIn("claude-opus-5", self._arms(result))
        self.assertNotIn("claude-opus-5-5", self._arms(result))

    def test_only_a_probe_failure_freezes_its_family(self):
        # R2-1 (#203 probe round 2): an id the catalogue does not list is a
        # catalogue mismatch — the probe answered — so nothing is frozen.
        # One of another tier is nonsensical, so it IS a failure (R3-2).
        doc = {**self.DEFAULTS, "defaults": {"opus": "claude-opus-9",
                                             "sonnet": "claude-sonnet-5"}}
        result, _ = self._compute(defaults=doc)
        self.assertNotIn("defaults_failed", result)
        self.assertEqual(result["defaults_mismatched"]["opus"]["class"], "not-available")
        doc = {**self.DEFAULTS, "defaults": {"opus": "claude-sonnet-5",
                                             "sonnet": "claude-sonnet-5"}}
        result, _ = self._compute(defaults=doc)
        self.assertEqual(result["defaults_failed"], {"opus": "wrong-tier"})
        self.assertNotIn("defaults_mismatched", result)
        doc = {**self.DEFAULTS, "defaults": {"sonnet": "claude-sonnet-5"},
               "errors": {"opus": "timeout"}}
        result, _ = self._compute(defaults=doc)
        self.assertEqual(result["defaults_failed"], {"opus": "timeout"})
        self.assertNotIn("claude-opus-5-5", self._arms(result))
        self.assertIn("claude-opus-5", self._arms(result))

    def test_a_clean_probe_publishes_no_failure_keys(self):
        result, _ = self._compute(defaults=self.DEFAULTS)
        self.assertNotIn("defaults_failed", result)
        self.assertNotIn("defaults_document_failed", result)


class TestPreviewNotSeatedOnAFailedProbe(_PreviewFixture):
    """F2 (#203 probe round 1), the reviewer's preview.py: a probe that
    fails for one week must not seat the newer-than-default model, or the
    next week's clean probe retires it again — a flip on no evidence."""

    def test_preview_a_failed_week_adds_nothing_so_nothing_flips_back(self):
        prev = {**self.PREV, "arms": [{"id": "claude-opus-5-5"},
                                      {"id": "claude-sonnet-5"}]}
        failed = {**self.D, "defaults": {"sonnet": "claude-sonnet-5"},
                  "errors": {"opus": "timeout"}}
        r1, _ = self._compute(defaults=failed, previous=prev, models=self._models(),
                              census=self._census(), now=self.NOW_OCT)
        self.assertEqual(r1["added_since_last"], [])
        self.assertNotIn("claude-opus-5-6", self._arms(r1))
        self.assertIn("no new seat on a failed probe",
                      self._reason(r1, "claude-opus-5-6", "excluded"))
        prev2 = {**prev, "arms": [{"id": a["id"]} for a in r1["arms"]]}
        r2, _ = self._compute(defaults=self.D, previous=prev2, models=self._models(),
                              census=self._census(), now=self.NOW_OCT)
        self.assertEqual(r2["retired_since_last"], [])
        self.assertEqual(self._arms(r2), self._arms(r1))


class TestFailedProbeIsLoud(_WeeklyLoop):
    """F3 (#203 probe round 1): the failure is in the published roster and
    near the top of the summary, where the reviewer looks."""

    def _failed(self, **overrides):
        doc = {**self.DEFAULTS, "defaults": {"sonnet": "claude-sonnet-5"},
               "errors": {"opus": "timeout", "fable": "no-init"}}
        doc.update(overrides)
        return self._compute(defaults=doc)[0]

    def test_the_summary_names_the_frozen_families_near_the_top(self):
        summary = roster.render_summary(self._failed())
        head = summary.splitlines()[:4]
        line = next((ln for ln in head if "probe" in ln), None)
        self.assertIsNotNone(line, head)
        self.assertIn("`fable` (no-init)", line)
        self.assertIn("`opus` (timeout)", line)
        self.assertIn("held", line)
        self.assertNotIn("::", summary)

    def test_a_whole_document_failure_names_its_class(self):
        result = self._compute(defaults={**self.DEFAULTS, "defaults": {},
                                         "errors": {}})[0]
        self.assertEqual(result["defaults_document_failed"], "no-defaults")
        head = "\n".join(roster.render_summary(result).splitlines()[:4])
        self.assertIn("no-defaults", head)

    def test_the_total_week_summary_is_loud(self):
        errors = {a: "no-init" for a in ("opus", "sonnet", "haiku", "fable")}

        def docs(k):
            doc = self._docs(k)
            if k == 2:
                doc["defaults"], doc["errors"] = {}, dict(errors)
            return doc

        out, _ = self._loop(_s5_usage, 3, docs)
        summary = roster.render_summary(out[2]["result"])
        self.assertIn("probe failed", summary.lower())
        for alias in errors:
            self.assertIn(f"`{alias}` (no-init)", summary)

    def test_a_clean_probe_adds_no_line(self):
        summary = roster.render_summary(self._compute(defaults=self.DEFAULTS)[0])
        self.assertNotIn("probe failed", summary.lower())


class TestMismatchSummaryLineSaysNotAProbeFailure(_RosterFixture):
    """R8-4 (#203 probe round 8): the mismatch summary line must say, in so
    many words, that it is not a probe failure — the exact text a mutant
    that dropped "; not a probe failure:" survived round 8's mutation pass
    with no test pinning it."""

    def test_the_mismatch_line_says_not_a_probe_failure(self):
        defaults = {**self.DEFAULTS, "defaults": {"opus": "claude-opus-9",
                                                  "sonnet": "claude-sonnet-5"}}
        result, _ = self._compute(defaults=defaults)
        summary = roster.render_summary(result)
        self.assertIn("**Vendor default not matched:**", summary)
        self.assertIn("Frozen this run, not a probe failure: seats held", summary)


class _ProposeStepFixture(unittest.TestCase):
    """The "Propose a roster change" step body, run hermetically with a stub
    `gh`: shared by the #203 probe-round tests below. No test methods of its
    own, so subclasses do not re-run each other's."""

    START = "# >>> defaults-failed note"
    END = "# <<< defaults-failed note"
    WARNING = "::warning::vendor-default probe failed for {n} {word}; their seats were held"
    MARKER = "<!-- skills-evals:roster-proposal -->"

    @staticmethod
    def _plural(n):
        """"family" at 1, "families" otherwise (#203 probe round 9, R9-3):
        the two `::warning::` lines must not read "for 1 families"."""
        return "family" if n == 1 else "families"

    def setUp(self):
        doc = yaml.safe_load(EVAL_WORKFLOW.read_text(encoding="utf-8"))
        self.run_body = next(s for s in doc["jobs"]["eval"]["steps"]
                             if s.get("name") == "Propose a roster change")["run"]
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)

    def _fragment(self):
        self.assertIn(self.START, self.run_body)
        return self.run_body[self.run_body.index(self.START):self.run_body.index(self.END)]

    def _latest(self, payload):
        path = self.tmp / "latest.json"
        path.write_text(payload if isinstance(payload, str) else json.dumps(payload),
                        encoding="utf-8")
        return path

    def _run_fragment(self, payload):
        script = ("set -euo pipefail\n" + f"computed={str(self._latest(payload))!r}\n"
                  + self._fragment()
                  + '\nprintf "COUNT=%s\\n" "$defaults_failed"'
                  + '\nprintf "NOTE=%s\\n" "$probe_note"\n')
        done = subprocess.run(["bash", "-c", script], capture_output=True, text=True,
                              timeout=30, env={"PATH": os.environ.get("PATH", "")})
        self.assertEqual(done.returncode, 0, done.stderr)
        return done.stdout

    def _run_step(self, latest, issues, cwd=None):
        """The whole step body with a stub `gh`, from the tracker listing to
        the "same" branch — which is as far as a "same" run goes. `cwd` is
        the step's working directory (default: the temp dir, which has no
        `scripts/`, so a "differs" run is rejected before publication)."""
        runner = self.tmp / "runner"
        (runner / "roster").mkdir(parents=True)
        (runner / "roster-inputs").mkdir()
        (runner / "roster" / "latest.json").write_text(json.dumps(latest), encoding="utf-8")
        (runner / "roster-inputs" / "summary.md").write_text("### Model roster\n",
                                                            encoding="utf-8")
        stub = self.tmp / "bin"
        stub.mkdir()
        (self.tmp / "issues.json").write_text(json.dumps([issues]), encoding="utf-8")
        gh = stub / "gh"
        gh.write_text(
            "#!/usr/bin/env bash\n"
            f"printf '%s\\n' \"$*\" >> {str(self.tmp / 'gh.log')!r}\n"
            f"if [ \"$1\" = api ]; then cat {str(self.tmp / 'issues.json')!r}; exit 0; fi\n"
            # R2-3: `_gh_fail` names one `gh <verb> <noun>` that fails.
            f"if [ \"$1 $2\" = {getattr(self, '_gh_fail', None) or '-'!r} ]; then "
            "echo 'HTTP 502' >&2; exit 1; fi\n"
            "prev=''\n"
            "for arg in \"$@\"; do\n"
            f"  if [ \"$prev\" = --body-file ]; then cat \"$arg\" > {str(self.tmp / 'body.md')!r}; fi\n"
            "  prev=\"$arg\"\n"
            "done\n", encoding="utf-8")
        gh.chmod(0o755)
        event = self.tmp / "event.json"
        event.write_text(json.dumps({"schedule": "0 7 * * 1"}), encoding="utf-8")
        env = {"PATH": f"{stub}{os.pathsep}{os.environ.get('PATH', '')}",
               "RUNNER_TEMP": str(runner), "GITHUB_EVENT_PATH": str(event),
               "REPO": "example/skills-evals", "RUN_ID": "1",
               "SERVER_URL": "https://github.example.com",
               "GITHUB_TOKEN": "t", "GH_TOKEN": "t"}
        done = subprocess.run(["bash", "-c", self.run_body], capture_output=True,
                              text=True, timeout=60, env=env, cwd=cwd or self.tmp)
        self.assertEqual(done.returncode, 0, done.stderr)
        log = (self.tmp / "gh.log").read_text(encoding="utf-8").splitlines()
        body = ((self.tmp / "body.md").read_text(encoding="utf-8")
                if (self.tmp / "body.md").exists() else None)
        return done.stdout, [ln for ln in log if not ln.startswith("api ")], body

    def _tracker(self):
        return [{"number": 7, "user": {"login": "github-actions[bot]", "type": "Bot"},
                 "body": self.MARKER}]

    FAILED = {"proposal": {"status": "same", "changes": []},
              "defaults_failed": {"opus": "timeout"}}

    # R2-3 (#203 probe round 2): a failed gh write in the frozen-`same`
    # branch warns with a fixed text and never fails the step.
    def _run_failing(self, fail, issues):
        self._gh_fail = fail
        return self._run_step(self.FAILED, issues)


class TestProposeStepOnAFailedProbe(_ProposeStepFixture):
    """F3 (#203 probe round 1): eval.yml's "Propose a roster change" step
    warns with a fixed text when the computed roster carries
    `defaults_failed`, and keeps the tracking issue open even on "same"."""

    @unittest.skipUnless(shutil.which("bash"), "needs bash")
    def test_a_failed_probe_warns_with_the_fixed_text(self):
        out = self._run_fragment({"proposal": {"status": "same"},
                                  "defaults_failed": {"opus": "timeout",
                                                      "sonnet": "no-init"}})
        self.assertIn(self.WARNING.format(n=2, word=self._plural(2)) + "\n", out)
        self.assertIn("COUNT=2\n", out)
        self.assertIn("NOTE=**The vendor-default probe failed", out)

    @unittest.skipUnless(shutil.which("bash"), "needs bash")
    def test_no_failure_or_a_junk_document_warns_nothing(self):
        for payload in ({"proposal": {"status": "same"}},
                        {"defaults_failed": ["opus"]},
                        {"defaults_failed": "::error::x"},
                        "{not json", "[1, 2]"):
            with self.subTest(payload=str(payload)[:30]):
                out = self._run_fragment(payload)
                self.assertNotIn("::warning::", out)
                self.assertIn("COUNT=0\n", out)
                self.assertIn("NOTE=\n", out)

    @unittest.skipUnless(shutil.which("bash"), "needs bash")
    def test_the_failed_note_reuses_the_singular_plural_word(self):
        # N2 (adv round 10): `failed_note` used to hardcode "families" even
        # at count 1; it now reuses `$failed_word`, same as the ::warning::.
        out = self._run_fragment({"proposal": {"status": "same"},
                                  "defaults_failed": {"opus": "timeout"}})
        self.assertIn("NOTE=**The vendor-default probe failed for 1 family this run.**",
                      out)
        out = self._run_fragment({"proposal": {"status": "same"},
                                  "defaults_failed": {"opus": "timeout",
                                                      "sonnet": "no-init"}})
        self.assertIn("NOTE=**The vendor-default probe failed for 2 families this "
                      "run.**", out)

    @unittest.skipUnless(shutil.which("bash"), "needs bash")
    def test_the_mismatch_note_reuses_the_singular_plural_word(self):
        out = self._run_fragment({"proposal": {"status": "same"},
                                  "defaults_mismatched": {"opus": {
                                      "id": "claude-opus-9", "class": "not-available"}}})
        self.assertIn("NOTE=**A vendor default did not match this run's catalogue "
                      "for 1 family this run.**", out)
        out = self._run_fragment({"proposal": {"status": "same"},
                                  "defaults_mismatched": {
                                      "opus": {"id": "claude-opus-9",
                                              "class": "not-available"},
                                      "sonnet": {"id": "claude-sonnet-9",
                                                "class": "not-available"}}})
        self.assertIn("NOTE=**A vendor default did not match this run's catalogue "
                      "for 2 families this run.**", out)

    def test_the_fragment_interpolates_nothing(self):
        fragment = self._fragment()
        self.assertNotIn("${{", fragment)
        # Each warning's text is fixed: the only expansion in each line is
        # the count that line's own case validated as digits, and the
        # singular/plural word chosen from that same count in shell (#203
        # probe round 9, R9-3: "for 1 families" must read "for 1 family")
        # — the failed count and word in the first ::warning:: line, the
        # mismatched count and word in the second (R8-1, #203 probe round 8).
        warning_lines = [ln for ln in fragment.splitlines() if "::warning::" in ln]
        self.assertEqual(len(warning_lines), 2, warning_lines)
        for line, var, word_var in zip(
                warning_lines, ("defaults_failed", "defaults_mismatched"),
                ("failed_word", "mismatched_word")):
            self.assertEqual(re.findall(r"\$\{?(\w+)", line), [var, word_var], line)

    @unittest.skipUnless(shutil.which("bash") and shutil.which("jq"), "needs bash and jq")
    def test_same_with_a_failed_probe_opens_the_issue(self):
        out, calls, body = self._run_step(self.FAILED, [])
        self.assertIn(self.WARNING.format(n=1, word=self._plural(1)), out)
        # R9-3 (#203 probe round 9): the singular reads "1 family", never
        # the plural "1 families".
        self.assertIn("for 1 family;", out)
        self.assertNotIn("for 1 families", out)
        self.assertEqual(len(calls), 1, calls)
        self.assertTrue(calls[0].startswith("issue create"), calls)
        self.assertIn("probe failed", calls[0])
        self.assertTrue(body.startswith(self.MARKER), body)
        # N2 (adv round 10): the note body reuses `$failed_word` too, so
        # the singular reads "1 family", never "1 families".
        self.assertIn("The vendor-default probe failed for 1 family this run", body)
        self.assertNotIn("for 1 families", body)
        self.assertIn("### Model roster", body)

    @unittest.skipUnless(shutil.which("bash") and shutil.which("jq"), "needs bash and jq")
    def test_same_with_a_failed_probe_keeps_an_open_issue_open(self):
        out, calls, body = self._run_step(self.FAILED, self._tracker())
        self.assertEqual(len(calls), 1, calls)
        self.assertTrue(calls[0].startswith("issue edit 7"), calls)
        self.assertFalse(any(c.startswith("issue close") for c in calls), calls)
        self.assertIn("probe failed", body)

    @unittest.skipUnless(shutil.which("bash") and shutil.which("jq"), "needs bash and jq")
    def test_same_with_a_clean_probe_still_closes_the_issue(self):
        out, calls, _ = self._run_step({"proposal": {"status": "same", "changes": []}},
                                       self._tracker())
        self.assertNotIn("::warning::", out)
        self.assertEqual(len(calls), 1, calls)
        self.assertTrue(calls[0].startswith("issue close 7"), calls)

    def test_the_differs_bodies_carry_the_probe_note(self):
        tail = self.run_body[self.run_body.index(self.END):]
        self.assertGreaterEqual(tail.count('"$probe_note"'), 3)

    @unittest.skipUnless(shutil.which("bash") and shutil.which("jq"), "needs bash and jq")
    def test_a_failed_create_warns_and_exits_zero(self):
        out, calls, _ = self._run_failing("issue create", [])
        self.assertTrue(calls[0].startswith("issue create"), calls)
        self.assertIn("::warning::could not create the roster tracking issue\n", out)

    @unittest.skipUnless(shutil.which("bash") and shutil.which("jq"), "needs bash and jq")
    def test_a_failed_edit_warns_and_exits_zero(self):
        out, calls, _ = self._run_failing("issue edit", self._tracker())
        self.assertTrue(calls[0].startswith("issue edit 7"), calls)
        self.assertIn("::warning::could not update the roster tracking issue\n", out)
        self.assertNotIn("updated the roster tracking issue", out)


class TestProposeStepOnAMismatch(_ProposeStepFixture):
    """R8-1 (#203 probe round 8): a catalogue mismatch with no probe
    failure is loud in the workflow exactly like a failure — its own fixed
    `::warning::`, its own probe-note sentence, and an open tracking issue
    even on "same" — but the issue's title and first line never say "probe
    failed" for a mismatch-only run, and name both classes when both are
    present. The reviewer's h1.py, h2.py and h3.py."""

    MISMATCH_WARNING = ("::warning::vendor default not matched by this run's "
                        "catalogue for {n} {word}; their seats were held")

    MISMATCHED = {"proposal": {"status": "same", "changes": []},
                 "defaults_mismatched": {"opus": {"id": "claude-opus-9",
                                                  "class": "not-available"}}}
    BOTH = {"proposal": {"status": "same", "changes": []},
           "defaults_failed": {"sonnet": "timeout"},
           "defaults_mismatched": {"opus": {"id": "claude-opus-9",
                                            "class": "not-available"}}}

    @unittest.skipUnless(shutil.which("bash") and shutil.which("jq"), "needs bash and jq")
    def test_a_mismatch_only_same_with_no_issue_creates_one(self):
        out, calls, body = self._run_step(self.MISMATCHED, [])
        self.assertIn(self.MISMATCH_WARNING.format(n=1, word=self._plural(1)), out)
        self.assertIn("for 1 family;", out)
        self.assertNotIn("for 1 families", out)
        self.assertEqual(len(calls), 1, calls)
        self.assertTrue(calls[0].startswith("issue create"), calls)
        self.assertNotIn("probe failed", calls[0])
        self.assertIn("did not match", calls[0])
        self.assertTrue(body.startswith(self.MARKER), body)
        self.assertNotIn("probe failed", body)
        self.assertIn("did not match this run's catalogue", body)
        self.assertIn("### Model roster", body)

    @unittest.skipUnless(shutil.which("bash") and shutil.which("jq"), "needs bash and jq")
    def test_a_mismatch_only_same_with_an_open_issue_edits_never_closes(self):
        out, calls, body = self._run_step(self.MISMATCHED, self._tracker())
        self.assertEqual(len(calls), 1, calls)
        self.assertTrue(calls[0].startswith("issue edit 7"), calls)
        self.assertFalse(any(c.startswith("issue close") for c in calls), calls)
        self.assertNotIn("probe failed", body)
        self.assertIn("did not match this run's catalogue", body)

    @unittest.skipUnless(shutil.which("bash") and shutil.which("jq"), "needs bash and jq")
    def test_both_classes_present_names_both_in_the_title_and_never_closes(self):
        out, calls, body = self._run_step(self.BOTH, [])
        self.assertIn(self.WARNING.format(n=1, word=self._plural(1)), out)
        self.assertIn(self.MISMATCH_WARNING.format(n=1, word=self._plural(1)), out)
        self.assertEqual(len(calls), 1, calls)
        self.assertTrue(calls[0].startswith("issue create"), calls)
        self.assertIn("probe failed", calls[0])
        self.assertIn("did not match", calls[0])
        self.assertFalse(any(c.startswith("issue close") for c in calls), calls)


class TestWorkflowProbeFallbackDocument(unittest.TestCase):
    """A probe that exits non-zero writes no document; the roster step then
    writes a stand-in in its place, so the roster freezes every family
    rather than reading "no probe at all" (F1 + F7, #203 probe round 1).
    The stand-in names its own class, `probe-exited` (R2-4, #203 probe
    round 2); an empty `{}` is a probe that ran and resolved nothing."""

    def test_a_failed_probe_leaves_a_document_that_freezes(self):
        doc = yaml.safe_load(EVAL_WORKFLOW.read_text(encoding="utf-8"))
        script = next(s for s in doc["jobs"]["eval"]["steps"]
                      if "roster" in (s.get("name") or "").lower())["run"]
        line = next(ln.strip() for ln in script.splitlines()
                    if "scripts/probe_model_defaults.py" in ln
                    and not ln.strip().startswith("#"))
        self.assertIn("|| printf '{\"probe_exit\": \"nonzero\"}\\n' "
                      "> \"$work/defaults.json\"", line)
        self.assertTrue(line.endswith("|| true"), line)
        result = roster.compute_roster(
            models_doc=_RosterFixture._models_doc(), census_doc=_RosterFixture._census(),
            policy=_RosterFixture._policy(), previous=copy.deepcopy(_RosterFixture.PREVIOUS),
            now=_RosterFixture.NOW, warn=lambda _m: None, defaults_doc={})
        self.assertEqual(result["defaults_document_failed"], "no-defaults")


class TestProbeKillsItsProcessGroup(_ProbeFixture):
    """F4 (#203 probe round 1): whatever the leader does, `_stop` SIGKILLs
    the whole process group — a child that ignores SIGTERM included."""

    def test_a_sigterm_ignoring_child_in_the_group_is_killed(self):
        pidfile = self.tmp / "child.pid"
        wrapper = self._wrapper("init-orphan-child",
                                extra_env={"FAKE_INIT_PIDFILE": str(pidfile)})
        policy = self._policy(["opus"])

        def gone(pid):
            try:
                os.kill(pid, 0)
            except ProcessLookupError:
                return True
            try:  # reparented and killed but not yet reaped: a zombie is gone
                stat = Path(f"/proc/{pid}/stat").read_text(encoding="utf-8")
                return stat.rsplit(")", 1)[1].split()[0] in ("Z", "X")
            except OSError:
                return True

        def reap():
            if pidfile.exists():
                with contextlib.suppress(ProcessLookupError, ValueError):
                    os.kill(int(pidfile.read_text(encoding="utf-8")), 9)

        self.addCleanup(reap)
        done, doc = self._probe(wrapper, "--policy", str(policy), "--timeout", "120",
                                timeout=60)
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertEqual(doc["defaults"], {"opus": self.RESOLVED["opus"]})
        pid = int(pidfile.read_text(encoding="utf-8"))
        # A short bounded wait on process state — the one sleep here, and
        # it is in the test, not in product code: SIGKILL delivery to a
        # reparented process is asynchronous.
        for _ in range(100):
            if gone(pid):
                break
            time.sleep(0.05)
        self.assertTrue(gone(pid), f"the group child {pid} survived the probe")


class TestProbeResolvesClaude(_ProbeFixture):
    """F7 (#203 probe round 1): `--claude` is resolved once, in main(), with
    `shutil.which` and then made absolute — so a relative path means what it
    meant in the caller's directory, not in the probe's temporary HOME."""

    def test_a_relative_claude_path_works(self):
        wrapper = self._wrapper()
        out = self.tmp / "defaults.json"
        done = subprocess.run(
            [sys.executable, str(PROBE), "--claude", f"./{wrapper.name}",
             "--policy", str(self._policy(["opus"])), "--out", str(out)],
            capture_output=True, text=True, timeout=120, cwd=self.tmp)
        self.assertEqual(done.returncode, 0, done.stderr)
        doc = json.loads(out.read_text(encoding="utf-8"))
        self.assertEqual(doc["defaults"], {"opus": self.RESOLVED["opus"]})
        self.assertEqual(doc["harness_version"], FAKE_VERSION_LINE)

    def test_a_bare_name_resolves_on_path(self):
        wrapper = self._wrapper()
        env = dict(os.environ, PATH=f"{self.tmp}{os.pathsep}{os.environ.get('PATH', '')}")
        done, doc = self._probe(wrapper.name, "--policy", str(self._policy(["opus"])),
                                env=env)
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertEqual(doc["defaults"], {"opus": self.RESOLVED["opus"]})


class TestUndatedDefaultMapsOntoADatedId(_RosterFixture):
    """F6 (#203 probe round 1): an undated id the catalogue does not list
    maps onto its ONE dated `<id>-YYYYMMDD`, mirroring the dated->undated
    collapse; none is "not available", two or more is ambiguous — and both
    of those are catalogue mismatches, which freeze the family exactly like
    a probe failure, in their own wording (R2-1, #203 probe round 2; R7-1,
    round 7)."""

    def _catalogue(self, *dated):
        return self._models_doc(drop=("claude-opus-5-5",), extra=[
            self._model(i, "x", "2026-09-26T12:00:00Z") for i in dated])

    def test_one_dated_candidate_resolves(self):
        # The reviewer's snap.py, first case.
        result, warnings = self._compute(
            defaults=self.DEFAULTS, models=self._catalogue("claude-opus-5-5-20260926"))
        self.assertEqual(result["defaults"]["resolved"]["opus"],
                         "claude-opus-5-5-20260926")
        self.assertEqual(result["defaults"]["unresolved"], [])
        self.assertIn("claude-opus-5-5-20260926", self._arms(result))
        self.assertIn("vendor default for the opus tier",
                      self._reason(result, "claude-opus-5-5-20260926"))
        self.assertNotIn("defaults_failed", result)

    def test_no_dated_candidate_is_not_available(self):
        result, _ = self._compute(defaults=self.DEFAULTS, models=self._catalogue())
        self.assertNotIn("defaults_failed", result)
        self.assertEqual(result["defaults_mismatched"]["opus"]["class"], "not-available")
        self.assertIn("not an available model",
                      result["defaults"]["unresolved"][0]["reason"])

    def test_two_dated_candidates_are_ambiguous_and_freeze(self):
        models = self._catalogue("claude-opus-5-5-20260926", "claude-opus-5-5-20261001")
        result, warnings = self._compute(defaults=self.DEFAULTS, models=models)
        self.assertNotIn("defaults_failed", result)
        self.assertEqual(result["defaults_mismatched"]["opus"]["class"],
                         "ambiguous-snapshot")
        self.assertNotIn("opus", result["defaults"]["resolved"])
        why = result["defaults"]["unresolved"][0]["reason"]
        self.assertIn("2 dated snapshots", why)
        # Frozen exactly like a probe failure (R7-1, #203 probe round 7):
        # opus-5, the listed previous arm, holds the seat; neither dated
        # snapshot of opus-5-5 earns one while it does.
        self.assertIn("claude-opus-5", self._arms(result))
        self.assertIn("held; none retired on a catalogue mismatch",
                      self._reason(result, "claude-opus-5"))
        for snap in ("claude-opus-5-5-20260926", "claude-opus-5-5-20261001"):
            self.assertNotIn(snap, self._arms(result))
            self.assertIn("no new seat on a catalogue mismatch while the family "
                          "holds a seat the Models API still lists",
                          self._reason(result, snap, "excluded"))

    def test_a_dated_id_of_another_base_is_not_a_candidate(self):
        # `claude-opus-5-20260101` is a snapshot of opus-5, not of opus-5-5.
        result, _ = self._compute(defaults=self.DEFAULTS, models=self._catalogue(
            "claude-opus-5-20260101"))
        self.assertNotIn("defaults_failed", result)
        self.assertEqual(result["defaults_mismatched"]["opus"]["class"], "not-available")


class TestNetworkWording(unittest.TestCase):
    """F5 (#203 probe round 1): the real CLI makes unauthenticated TLS
    connections before and after init; the docs must not say nothing is
    sent, and the "cannot run either" claim was false."""

    FILES = ("README.md", "DESIGN.md",
             "docs/decisions/0002-roster-follows-vendor-defaults.md",
             "scripts/probe_model_defaults.py", ".github/workflows/eval.yml",
             "evals/roster-policy.yml", "harness/roster.py")
    STALE = ("nothing is sent", "sends nothing", "before it can try the api",
             "never left to try the api", "cannot run either",
             "eval cannot run", "carries nothing over")

    def test_no_stale_claim_survives(self):
        for rel in self.FILES:
            flat = " ".join((REPO_ROOT / rel).read_text(encoding="utf-8").lower().split())
            flat = re.sub(r"\s*#\s*", " ", flat)
            for stale in self.STALE:
                with self.subTest(file=rel, stale=stale):
                    self.assertNotIn(stale, flat)

    def test_the_docs_say_what_is_true_instead(self):
        for rel in ("README.md", "DESIGN.md",
                    "docs/decisions/0002-roster-follows-vendor-defaults.md",
                    "scripts/probe_model_defaults.py"):
            flat = " ".join((REPO_ROOT / rel).read_text(encoding="utf-8").split())
            with self.subTest(file=rel):
                self.assertIn("no credential", flat)
                self.assertIn("frozen", flat.lower())


# --- #203 probe round 2 -------------------------------------------------------


def _mismatch_words(model_id, alias, cls):
    return (f"the CLI's default `{model_id}` for `{alias}` does not match this "
            f"run's catalogue ({cls})")


class TestCatalogueMismatchFreezesLikeAFailure(_WeeklyLoop):
    """R2-1(a) (#203 probe round 2), superseded by R7-1 (round 7): the probe
    ANSWERED for an alias, but this run's Models API catalogue does not
    match the answer. That is not a probe FAILURE, but since round 7 it
    FREEZES the family exactly the same way a failure does (the reviewer's
    g2.py, g3.py: a mismatch week changes no seat a clean week would not),
    replacing round 4's guessed "effective default". The wording still
    says what happened, never "probe failed" or "unknown this run". A
    wrong-tier or wrong-family answer is a failure since R3-2: see
    TestMismatchGetsNoNewestInTierSeat."""

    def _clean_baseline(self, **kwargs):
        # A clean probe naming opus-5 directly: the same listed previous
        # arm the freeze below holds, so a one-week mismatch changes no
        # seat this clean run would not (the governing guarantee, R7-1).
        return self._compute(defaults={**self.DEFAULTS, "skipped": [],
                                       "defaults": {"opus": "claude-opus-5"}},
                             **kwargs)[0]

    def _assert_frozen_as_the_clean_run_would_seat(self, result, baseline, alias):
        self.assertNotIn("defaults_failed", result)
        self.assertNotIn("defaults_document_failed", result)
        self.assertEqual(self._arms(result), self._arms(baseline))
        self.assertEqual(result["retired_since_last"], baseline["retired_since_last"])
        self.assertIn(alias, result["defaults_mismatched"])

    def test_each_mismatch_class_freezes_like_the_clean_run_would_seat(self):
        # `no-created-at` is a PROBE FAILURE since R5-1 (#203 probe round
        # 5), not a mismatch class: see TestNoCreatedAtIsAProbeFailure.
        cases = (
            ("not-available", {"opus": "claude-opus-9"}, "opus", {}),
            ("ambiguous-snapshot", {"opus": "claude-opus-5-5"}, "opus",
             {"models": self._models_doc(drop=("claude-opus-5-5",), extra=[
                 self._model("claude-opus-5-5-20260926", "x", "2026-09-26T12:00:00Z"),
                 self._model("claude-opus-5-5-20261001", "x", "2026-09-26T12:00:00Z")])}),
        )
        for cls, defaults, alias, kwargs in cases:
            with self.subTest(cls=cls):
                baseline = self._clean_baseline(**kwargs)
                result, warnings = self._compute(
                    defaults={**self.DEFAULTS, "defaults": defaults,
                              "skipped": []}, **kwargs)
                self._assert_frozen_as_the_clean_run_would_seat(result, baseline, alias)
                self.assertEqual(result["defaults_mismatched"][alias]["class"], cls)
                self.assertEqual(result["defaults_mismatched"][alias]["id"],
                                 defaults[alias])
                said = _mismatch_words(defaults[alias], alias, cls)
                self.assertTrue(any(said in w for w in warnings), warnings)
                summary = roster.render_summary(result)
                self.assertIn(said, summary)
                self.assertIn("held; none retired on a catalogue mismatch",
                              self._reason(result, "claude-opus-5"))
                text = "\n".join(warnings) + summary
                self.assertNotIn("probe failed", text.lower())
                self.assertNotIn("unknown this run", text)

    def test_scenario_a_a_persistent_mismatch_holds_the_listed_seat_and_says_so(self):
        # The reviewer's loop.py A, updated for R5-2 (#203 probe round 5):
        # the CLI says opus is an id this bearer never lists, while opus-5
        # (a previous arm, from `PREV0`) is still listed and opus-5-5 (newer,
        # heavily used) is not yet one. The listed seat holds — opus-5-5
        # earns no seat while it remains listed — and the wording says so.
        def usage(n):
            return {"claude-sonnet-5": 900, "claude-haiku-4-5": 50,
                    "claude-fable-5-1": 0, "claude-opus-5": 0,
                    "claude-opus-5-5": 400}

        out, _ = self._loop(usage, 1, lambda k: self._docs(
            k, opus="claude-opus-6", sonnet="claude-sonnet-5",
            haiku="claude-haiku-4-5"))
        week0 = out[0]["result"]
        self.assertNotIn("defaults_failed", week0)
        self.assertIn("claude-opus-5", self._arms(week0))
        self.assertNotIn("claude-opus-5-5", self._arms(week0))
        said = _mismatch_words("claude-opus-6", "opus", "not-available")
        self.assertIn(said, self._reason(week0, "claude-opus-5"))
        self.assertTrue(any(said in w for w in out[0]["warnings"]), out[0]["warnings"])
        head = "\n".join(roster.render_summary(week0).splitlines()[:4])
        self.assertIn(said, head)

    def test_a_probe_error_still_freezes(self):
        doc = {**self.DEFAULTS, "defaults": {"sonnet": "claude-sonnet-5"},
               "errors": {"opus": "timeout"}}
        result, _ = self._compute(defaults=doc)
        self.assertEqual(result["defaults_failed"], {"opus": "timeout"})
        self.assertNotIn("defaults_mismatched", result)

    def test_a_clean_probe_publishes_no_mismatch_key(self):
        result, _ = self._compute(defaults=self.DEFAULTS)
        self.assertNotIn("defaults_mismatched", result)


class TestDatedDefaultOntoUndated(_WeeklyLoop):
    """R2-1(b) (#203 probe round 2): the probe answers a dated
    `<base>-YYYYMMDD` the catalogue does not list, while it lists `<base>`:
    the default resolves onto `<base>` (the mirror of round 1's F6)."""

    def test_one_run(self):
        defaults = {**self.DEFAULTS, "defaults": {**self.DEFAULTS["defaults"],
                                                  "haiku": "claude-haiku-4-5-20251001"}}
        result, warnings = self._compute(defaults=defaults)
        self.assertEqual(result["defaults"]["resolved"]["haiku"], "claude-haiku-4-5")
        self.assertNotIn("defaults_failed", result)
        self.assertNotIn("defaults_mismatched", result)
        self.assertFalse(any("haiku" in w for w in warnings), warnings)

    def test_scenario_b_haiku_at_40_percent_is_seated(self):
        # The reviewer's loop.py B.
        def usage(n):
            return {"claude-sonnet-5": 500, "claude-haiku-4-5": 600,
                    "claude-opus-5": 400, "claude-opus-5-5": 0}

        out, _ = self._loop(usage, 3, lambda k: self._docs(
            k, opus="claude-opus-5", sonnet="claude-sonnet-5",
            haiku="claude-haiku-4-5-20251001"))
        for k, week in enumerate(out):
            self.assertIn("claude-haiku-4-5", self._arms(week["result"]), k)
            self.assertNotIn("defaults_failed", week["result"], k)
        self.assertIn("vendor default for the haiku tier",
                      self._reason(out[0]["result"], "claude-haiku-4-5"))


class TestFrozenFamilyStillSeatsByUsage(_WeeklyLoop):
    """R2-1(c) (#203 probe round 2), narrowed by R3-1 (round 3): a frozen
    family retires nothing (but a model gone from the Models API). While it
    still holds a seat the Models API lists it gets no new seat at all;
    once it holds none, a model of it that clears the usage ENTRY bar is
    seated, so the roster never loses the family the fleet moved to."""

    NEW = [_RosterFixture._model("claude-sonnet-6", "S6", "2026-10-05T00:00:00Z"),
           _RosterFixture._model("claude-opus-6", "O6", "2026-10-05T00:00:00Z")]

    @staticmethod
    def _no_init(k):
        return {"probed_at": "2026-10-01T00:00:00Z",
                "harness_version": "3.0.0 (Claude Code)", "defaults": {},
                "skipped": [], "errors": {a: "no-init" for a in
                                          ("haiku", "sonnet", "opus", "fable", "mythos")}}

    @staticmethod
    def _usage(n):
        return {"claude-sonnet-6": 900, "claude-opus-6": 800,
                "claude-sonnet-5": 0, "claude-opus-5": 0}

    def test_scenario_c_every_alias_no_init_while_the_fleet_moves(self):
        # The reviewer's whole.py, chained: three weeks with both
        # generations listed, then the old ones leave the Models API.
        models = list(self.BASE) + list(self.NEW)
        out, prev = self._loop(self._usage, 3, self._no_init, models=models)
        week0 = out[0]["result"]
        # R3-1: the old arms are still listed, so the families are on the
        # roster and a failed probe adds nothing — not even opus-6 at 47%.
        self.assertEqual(sorted(self._arms(week0)), ["claude-opus-5", "claude-sonnet-5"])
        self.assertEqual(week0["retired_since_last"], [])
        # Old arms are held although they are at 0%: a freeze never removes.
        self.assertIn("held; none retired on a failed probe",
                      self._reason(week0, "claude-opus-5"))
        for model_id in ("claude-opus-6", "claude-sonnet-6", "claude-opus-5-5"):
            self.assertIn("no new seat on a failed probe while the family holds a "
                          "seat the Models API still lists",
                          self._reason(week0, model_id, "excluded"))
        # haiku and fable hold no seat: only the entry bar could seat them.
        for model_id in ("claude-haiku-4-5", "claude-fable-5-1"):
            self.assertNotIn(model_id, self._arms(week0))
            self.assertIn("no new seat on a failed probe but by the",
                          self._reason(week0, model_id, "excluded"))
        for week in out[1:]:
            self.assertEqual(week["result"]["retired_since_last"], [])
            self.assertEqual(sorted(self._arms(week["result"])),
                             sorted(self._arms(week0)))
        gone = [m for m in models if m["id"] not in ("claude-sonnet-5", "claude-opus-5")]
        out2, _ = self._loop(self._usage, 1, self._no_init, previous=prev, models=gone)
        last = out2[0]["result"]
        self.assertEqual(sorted(self._arms(last)), ["claude-opus-6", "claude-sonnet-6"])
        self.assertEqual(sorted(r["id"] for r in last["retired_since_last"]),
                         ["claude-opus-5", "claude-sonnet-5"])
        for entry in last["retired_since_last"]:
            self.assertEqual(entry["reason"], "no longer returned by the Models API")

    def test_scenario_c_from_the_seed_roster_is_never_empty(self):
        # whole.py exactly: the old generation already gone at week 0.
        gone = [m for m in list(self.BASE) + list(self.NEW)
                if m["id"] not in ("claude-sonnet-5", "claude-opus-5")]
        out, _ = self._loop(self._usage, 2, self._no_init, models=gone)
        for week in out:
            self.assertEqual(sorted(self._arms(week["result"])),
                             ["claude-opus-6", "claude-sonnet-6"])

    def test_a_frozen_seat_by_usage_says_the_probe_failed(self):
        models = [m for m in list(self.BASE) + list(self.NEW)
                  if m["id"] not in ("claude-sonnet-5", "claude-opus-5")]
        out, _ = self._loop(self._usage, 1, self._no_init, models=models)
        why = self._reason(out[0]["result"], "claude-opus-6")
        self.assertIn("unknown this run (probe: no-init)", why)
        self.assertIn("entry bar", why)


class TestProbeExitedDocument(_RosterFixture):
    """R2-4 (#203 probe round 2): eval.yml's stand-in for a probe that
    exited non-zero is its own class, `probe-exited` — a probe failure that
    freezes — while `{}` from a probe that ran stays `no-defaults`."""

    def test_the_stand_in_freezes_as_probe_exited(self):
        result, warnings = self._compute(defaults={"probe_exit": "nonzero"})
        self.assertEqual(result["defaults_document_failed"], "probe-exited")
        self.assertEqual(result["defaults_failed"],
                         {w: "probe-exited" for w in roster.tier_words(self._policy())})
        self.assertEqual(sorted(self._arms(result)), ["claude-opus-5", "claude-sonnet-5"])
        self.assertTrue(any("the probe script exited with an error" in w
                            for w in warnings), warnings)
        self.assertIn("the probe script exited with an error",
                      roster.render_summary(result))

    def test_an_empty_document_stays_no_defaults(self):
        result, _ = self._compute(defaults={})
        self.assertEqual(result["defaults_document_failed"], "no-defaults")

    def test_the_workflow_writes_the_stand_in(self):
        doc = yaml.safe_load(EVAL_WORKFLOW.read_text(encoding="utf-8"))
        script = next(s for s in doc["jobs"]["eval"]["steps"]
                      if s.get("name") == "Refresh the model roster")["run"]
        line = next(ln.strip() for ln in script.splitlines()
                    if "scripts/probe_model_defaults.py" in ln
                    and not ln.strip().startswith("#"))
        self.assertIn("|| printf '{\"probe_exit\": \"nonzero\"}\\n' > \"$work/defaults.json\"",
                      line)
        self.assertTrue(line.endswith("|| true"), line)
        stand_in = json.loads('{"probe_exit": "nonzero"}')
        result, _ = self._compute(defaults=stand_in)
        self.assertEqual(result["defaults_document_failed"], "probe-exited")


class TestProposeStepRunsUnlessCancelled(unittest.TestCase):
    """R2-2 (#203 probe round 2): the loud channels — the proposal step's
    warning and tracking issue — fire even when a later-listed step before
    it (the eval) failed, but never on a cancelled workflow."""

    def _step(self):
        doc = yaml.safe_load(EVAL_WORKFLOW.read_text(encoding="utf-8"))
        return next(s for s in doc["jobs"]["eval"]["steps"]
                    if s.get("name") == "Propose a roster change")

    def test_the_step_runs_unless_cancelled(self):
        condition = " ".join(str(self._step().get("if", "")).split())
        self.assertEqual(condition, "${{ !cancelled() }}")
        self.assertNotIn("always()", condition)

    def test_it_still_handles_a_missing_roster(self):
        body = self._step()["run"]
        self.assertIn('if [ ! -f "$computed" ]; then', body)

    def test_the_docs_say_what_fires(self):
        for path in (EVAL_WORKFLOW,
                     REPO_ROOT / "docs" / "decisions"
                     / "0002-roster-follows-vendor-defaults.md"):
            flat = " ".join(path.read_text(encoding="utf-8").split())
            flat = re.sub(r"\s*#\s*", " ", flat)
            with self.subTest(path=path.name):
                self.assertIn("unless the workflow is cancelled", flat)


class TestHarnessVersionKillsItsGroup(_ProbeFixture):
    """R2-5 (#203 probe round 2): `claude --version` runs through the same
    new-session Popen and `_stop` as the alias probes, so a forked child
    holding stdout is killed and the timeout is enforced."""

    def _fake(self, *, print_version):
        pidfile = self.tmp / "verchild.pid"
        path = self.tmp / "claude-verchild"
        path.write_text(
            f"#!{sys.executable}\n"
            "import os, sys, time\n"
            "if '--version' in sys.argv:\n"
            "    pid = os.fork()\n"
            "    if pid == 0:\n"
            "        time.sleep(120)\n"
            "        os._exit(0)\n"
            f"    open({str(pidfile)!r}, 'w').write(str(pid))\n"
            + ("    print('9.9.9', flush=True)\n" if print_version else "")
            + "    os._exit(0)\n"
            "sys.exit(1)\n", encoding="utf-8")
        path.chmod(0o755)
        return path, pidfile

    @staticmethod
    def _gone(pid):
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            return True
        try:
            stat = Path(f"/proc/{pid}/stat").read_text(encoding="utf-8")
            return stat.rsplit(")", 1)[1].split()[0] in ("Z", "X")
        except OSError:
            return True

    def _check(self, print_version, timeout, expected):
        import probe_model_defaults
        fake, pidfile = self._fake(print_version=print_version)

        def reap():
            if pidfile.exists():
                with contextlib.suppress(ProcessLookupError, ValueError):
                    os.kill(int(pidfile.read_text(encoding="utf-8")), 9)

        self.addCleanup(reap)
        started = time.monotonic()
        version = probe_model_defaults.harness_version(str(fake), timeout)
        elapsed = time.monotonic() - started
        self.assertEqual(version, expected)
        pid = int(pidfile.read_text(encoding="utf-8"))
        for _ in range(100):  # bounded wait on process state, as above
            if self._gone(pid):
                break
            time.sleep(0.05)
        self.assertTrue(self._gone(pid), f"the --version child {pid} survived")
        return elapsed

    def test_a_forked_child_holding_stdout_is_killed(self):
        elapsed = self._check(True, 30.0, "9.9.9")
        self.assertLess(elapsed, 15.0)

    def test_the_timeout_is_enforced_without_a_version_line(self):
        elapsed = self._check(False, 1.0, None)
        self.assertLess(elapsed, 15.0)

    def test_the_docstring_names_the_setsid_escape(self):
        text = " ".join(PROBE.read_text(encoding="utf-8").split())
        self.assertIn("setsid()", text)
        self.assertIn("escapes the process-group kill", text)


class TestRound2Docs(unittest.TestCase):
    """R2-6 (#203 probe round 2): the stale claims are gone."""

    STALE = {
        "HANDOFF.md": ("a failed probe falls back to the usage rules",),
        "evals/roster-policy.yml": ("a tier with no resolved vendor default, e.g. haiku",),
    }

    def test_no_stale_claim_survives(self):
        for rel, stale in self.STALE.items():
            flat = " ".join((REPO_ROOT / rel).read_text(encoding="utf-8").split())
            flat = re.sub(r"\s*#\s*", " ", flat)
            for claim in stale:
                with self.subTest(file=rel, claim=claim):
                    self.assertNotIn(claim, flat)


# --- #203 probe round 3 -------------------------------------------------------


def _failed_doc(skipped=("mythos",)):
    """Every ladder alias the probe did not skip failed with `no-init`."""
    return {"probed_at": "2026-10-01T00:00:00Z",
            "harness_version": "2.1.283 (Claude Code)", "defaults": {},
            "skipped": list(skipped),
            "errors": {a: "no-init" for a in ("haiku", "sonnet", "opus", "fable", "mythos")
                       if a not in skipped}}


class TestFreezeSeatsByUsageOnlyWhenTheFamilyHoldsNothing(_WeeklyLoop):
    """R3-1 (#203 probe round 3): in a frozen family a model clearing the
    usage entry bar is seated ONLY when the family holds no previous arm the
    Models API still lists this run — the "the roster would lose the family"
    case. Otherwise a frozen family gets no new seat at all, so a one-week
    failure can never add a seat the next clean week retires."""

    def _clean(self, opus):
        return lambda k: self._docs(k, opus=opus, sonnet="claude-sonnet-5",
                                    haiku="claude-haiku-4-5")

    def _weeks(self, out):
        return [self._arms(week["result"]) for week in out]

    def test_s1_a_superseded_model_is_not_seated_on_a_failed_week(self):
        # The reviewer's s1.py: default opus-5-5 seated; opus-5 (superseded)
        # still carries 30%; the probe fails in week 1 only.
        def usage(n):
            return {"claude-sonnet-5": 500, "claude-opus-5": 300,
                    "claude-opus-5-5": 200, "claude-haiku-4-5": 0}

        prev = dict(self.PREV0, arms=[{"id": "claude-sonnet-5"},
                                      {"id": "claude-opus-5-5"}])
        clean = self._clean("claude-opus-5-5")
        base, _ = self._loop(usage, 6, clean, previous=prev)
        out, _ = self._loop(usage, 6, lambda k: _failed_doc() if k == 1 else clean(k),
                            previous=prev)
        self.assertEqual(self._weeks(out), self._weeks(base))
        week1 = out[1]["result"]
        self.assertIn("opus", week1["defaults_failed"])
        self.assertEqual(week1["added_since_last"], [])
        self.assertIn("no new seat on a failed probe while the family holds a seat "
                      "the Models API still lists",
                      self._reason(week1, "claude-opus-5", "excluded"))
        for week in out:
            self.assertEqual(week["result"]["retired_since_last"], [])

    def test_s2_a_preview_is_not_seated_on_a_failed_week(self):
        # The reviewer's s2.py: default opus-5 seated; the fleet runs the
        # preview opus-5-5 at 30% via --model.
        def usage(n):
            return {"claude-sonnet-5": 500, "claude-opus-5": 200, "claude-opus-5-5": 300}

        prev = dict(self.PREV0, arms=[{"id": "claude-sonnet-5"}, {"id": "claude-opus-5"}])
        clean = self._clean("claude-opus-5")
        base, _ = self._loop(usage, 4, clean, previous=prev)
        out, _ = self._loop(usage, 4, lambda k: _failed_doc() if k == 1 else clean(k),
                            previous=prev)
        self.assertEqual(self._weeks(out), self._weeks(base))
        self.assertEqual(out[1]["result"]["added_since_last"], [])
        self.assertNotIn("claude-opus-5-5", self._arms(out[1]["result"]))

    def _gone_models(self):
        return ([m for m in self.BASE if m["id"] not in ("claude-sonnet-5", "claude-opus-5")]
                + [self._model("claude-sonnet-6", "S6", "2026-09-01T00:00:00Z"),
                   self._model("claude-opus-6", "O6", "2026-09-01T00:00:00Z")])

    def test_the_usage_seat_boundary_is_the_entry_bar_inclusive(self):
        # R3-7(b): with no held arm left in the API, a share EXACTLY at
        # `arm_enter_usage_pct` is seated — the same `>=` as rule 1.
        for opus6, seated in ((100, True), (99, False)):
            with self.subTest(opus6=opus6):
                def usage(n, opus6=opus6):
                    return {"claude-sonnet-6": 1000 - opus6, "claude-opus-6": opus6}

                out, _ = self._loop(usage, 1, lambda k: _failed_doc(skipped=()),
                                    models=self._gone_models())
                result = out[0]["result"]
                self.assertIn("opus", result["defaults_failed"])
                self.assertEqual("claude-opus-6" in self._arms(result), seated)
                if seated:
                    why = self._reason(result, "claude-opus-6")
                    self.assertIn("carries 10.0% of rankable census usage", why)
                    self.assertIn("holds no seat the Models API still lists", why)
                else:
                    self.assertIn("usage entry bar",
                                  self._reason(result, "claude-opus-6", "excluded"))


class TestFrozenFamilyFallsBackWithNoCensus(_RosterFixture):
    """R3-6 (#203 probe round 3): with no usable enter window, a frozen
    family holding no seat the Models API still lists falls back to newest
    per tier, as the no-probe fallback does — a freeze never empties the
    roster where no probe at all would not."""

    NOW5 = datetime(2026, 10, 5, 12, tzinfo=timezone.utc)
    PREV = {**_RosterFixture.PREVIOUS,
            "arms": [{"id": "claude-sonnet-5"}, {"id": "claude-opus-5"}]}

    def _run(self, models, defaults):
        warnings: list[str] = []
        result = roster.compute_roster(
            models_doc={"fetched_at": self.NOW5.isoformat(), "models": models},
            census_doc=None, policy=self._policy(), previous=copy.deepcopy(self.PREV),
            now=self.NOW5, warn=warnings.append, defaults_doc=defaults)
        return result

    def test_s5_a_failed_probe_seats_what_no_probe_would(self):
        models = [self._model("claude-haiku-5", "H5", "2026-09-01T00:00:00Z"),
                  self._model("claude-sonnet-6", "S6", "2026-09-01T00:00:00Z"),
                  self._model("claude-opus-6", "O6", "2026-09-01T00:00:00Z")]
        no_probe = self._run(models, None)
        failed = self._run(models, _failed_doc())
        self.assertEqual(self._arms(failed), self._arms(no_probe))
        self.assertEqual(sorted(self._arms(failed)),
                         ["claude-haiku-5", "claude-opus-6", "claude-sonnet-6"])
        self.assertIn("falls back to newest per tier as with no probe",
                      self._reason(failed, "claude-opus-6"))
        self.assertIn("unknown this run (probe: no-init)",
                      self._reason(failed, "claude-opus-6"))

    def test_a_held_arm_still_blocks_the_fallback(self):
        models = [self._model("claude-sonnet-6", "S6", "2026-09-01T00:00:00Z"),
                  self._model("claude-opus-5", "O5", "2026-04-01T00:00:00Z"),
                  self._model("claude-opus-6", "O6", "2026-09-01T00:00:00Z")]
        failed = self._run(models, _failed_doc())
        self.assertIn("claude-opus-5", self._arms(failed))
        self.assertNotIn("claude-opus-6", self._arms(failed))
        self.assertIn("claude-sonnet-6", self._arms(failed))


class TestMismatchKeepsTheNoCensusFallback(_RosterFixture):
    """R3-6's guard, kept for a mismatch too (#203 probe rounds 3 and 7,
    R7-1): with no usable enter window a mismatched family holding no seat
    the Models API still lists keeps the no-probe fallback (its newest
    model), so a mismatch never empties the family either; holding one, the
    freeze holds that seat and nothing newer is seated."""

    NOW5 = TestFrozenFamilyFallsBackWithNoCensus.NOW5
    PREV = TestFrozenFamilyFallsBackWithNoCensus.PREV
    _run = TestFrozenFamilyFallsBackWithNoCensus._run

    MISMATCH = {"probed_at": "2026-10-01T00:00:00Z",
                "harness_version": "2.1.283 (Claude Code)",
                "defaults": {"opus": "claude-opus-9"}, "skipped": ["mythos"],
                "errors": {}}

    def test_s5_a_mismatch_seats_what_no_probe_would(self):
        models = [self._model("claude-sonnet-6", "S6", "2026-09-01T00:00:00Z"),
                  self._model("claude-opus-6", "O6", "2026-09-01T00:00:00Z")]
        no_probe = self._run(models, None)
        result = self._run(models, self.MISMATCH)
        self.assertEqual(result["defaults_mismatched"]["opus"]["class"], "not-available")
        self.assertEqual(self._arms(result), self._arms(no_probe))
        self.assertIn("claude-opus-6", self._arms(result))

    def test_a_held_arm_blocks_the_newest_seat(self):
        models = [self._model("claude-sonnet-6", "S6", "2026-09-01T00:00:00Z"),
                  self._model("claude-opus-5", "O5", "2026-04-01T00:00:00Z"),
                  self._model("claude-opus-6", "O6", "2026-09-01T00:00:00Z")]
        result = self._run(models, self.MISMATCH)
        self.assertIn("claude-opus-5", self._arms(result))
        self.assertNotIn("claude-opus-6", self._arms(result))
        self.assertIn("no new seat on a catalogue mismatch while the family "
                      "holds a seat the Models API still lists",
                      self._reason(result, "claude-opus-6", "excluded"))


class TestMismatchGetsNoNewestInTierSeat(_WeeklyLoop):
    """R3-2 (#203 probe round 3), as decided since R7-1 (round 7) and
    narrowed by R5-1 (round 5, `no-created-at` is now a probe failure, not a
    mismatch class): a CATALOGUE MISMATCH (not-available, ambiguous-snapshot)
    FREEZES its family exactly like a probe failure, so a model newer than
    the listed previous arm it holds gets no new seat, and a one-week
    mismatch adds nothing the next week retires."""

    @staticmethod
    def _usage(n):
        return {"claude-sonnet-5": 500, "claude-opus-5": 300, "claude-opus-5-5": 0}

    def _clean(self, k):
        return self._docs(k, opus="claude-opus-5", sonnet="claude-sonnet-5",
                          haiku="claude-haiku-4-5")

    def test_s3_a_one_week_mismatch_adds_and_flips_nothing(self):
        # `no-created-at` moved to TestNoCreatedAtIsAProbeFailure (R5-1,
        # #203 probe round 5): it is a probe failure now, not this class.
        dated = "2026-09-01T00:00:00Z"
        cases = (
            ("not-available", "claude-opus-6", list(self.BASE)),
            ("ambiguous-snapshot", "claude-opus-7",
             list(self.BASE) + [self._model("claude-opus-7-20260901", "O7", dated),
                                self._model("claude-opus-7-20260902", "O7", dated)]),
        )
        for cls, bad, models in cases:
            with self.subTest(cls=cls):
                base, _ = self._loop(self._usage, 4, self._clean, models=models)
                out, _ = self._loop(
                    self._usage, 4,
                    lambda k: self._docs(k, opus=bad, sonnet="claude-sonnet-5",
                                         haiku="claude-haiku-4-5") if k == 1
                    else self._clean(k), models=models)
                self.assertEqual([self._arms(w["result"]) for w in out],
                                 [self._arms(w["result"]) for w in base])
                week1 = out[1]["result"]
                self.assertEqual(week1["defaults_mismatched"]["opus"]["class"], cls)
                self.assertNotIn("defaults_failed", week1)
                self.assertEqual(week1["added_since_last"], [])
                self.assertEqual(out[2]["result"]["retired_since_last"], [])
                self.assertIn("held; none retired on a catalogue mismatch",
                              self._reason(week1, "claude-opus-5"))
                held_seat = ("no new seat on a catalogue mismatch while the family "
                            "holds a seat the Models API still lists")
                newer = [e for e in week1["excluded"] if held_seat in e["reason"]]
                self.assertTrue(newer, week1["excluded"])
                for entry in newer:
                    self.assertIn(_mismatch_words(bad, "opus", cls), entry["reason"])

    def test_a_mismatch_holds_the_listed_seat_and_seats_no_newer_used_model(self):
        # Round 2's loop.py A, updated for R5-2 (#203 probe round 5): opus-5
        # (a previous arm, still listed) HOLDS the seat; opus-5-5 (newer,
        # 30%-used, not yet a previous arm) earns no seat while opus-5
        # remains listed — the governing guarantee wins over seating the
        # model the fleet actually uses.
        def usage(n):
            return {"claude-sonnet-5": 900, "claude-opus-5": 0, "claude-opus-5-5": 400}

        out, _ = self._loop(usage, 1, lambda k: self._docs(
            k, opus="claude-opus-6", sonnet="claude-sonnet-5"))
        week0 = out[0]["result"]
        self.assertIn("held; none retired on a catalogue mismatch",
                      self._reason(week0, "claude-opus-5"))
        self.assertIn("no new seat on a catalogue mismatch while the family "
                      "holds a seat the Models API still lists",
                      self._reason(week0, "claude-opus-5-5", "excluded"))

    def test_wrong_tier_is_a_probe_failure_and_freezes(self):
        base, _ = self._loop(self._usage, 3, self._clean)
        out, _ = self._loop(self._usage, 3, lambda k: self._docs(
            k, opus="claude-sonnet-5", sonnet="claude-sonnet-5",
            haiku="claude-haiku-4-5") if k == 1 else self._clean(k))
        self.assertEqual([self._arms(w["result"]) for w in out],
                         [self._arms(w["result"]) for w in base])
        week1 = out[1]["result"]
        self.assertEqual(week1["defaults_failed"], {"opus": "wrong-tier"})
        self.assertNotIn("defaults_mismatched", week1)
        self.assertEqual(week1["added_since_last"], [])
        said = [w for w in out[1]["warnings"] if "`opus`" in w]
        self.assertTrue(any("nonsensical" in w and "treated as a probe failure" in w
                            for w in said), said)
        self.assertIn("vendor-default probe failed", roster.render_summary(week1))

    def test_wrong_family_is_a_probe_failure_and_freezes(self):
        policy = self._policy(tiers=["haiku", "sonnet", "opus", ["fable", "mythos"]])
        warnings: list[str] = []
        result = roster.compute_roster(
            models_doc=self._models_doc(), census_doc=self._census(), policy=policy,
            previous=copy.deepcopy(self.PREVIOUS), now=self.NOW, warn=warnings.append,
            defaults_doc={**self.DEFAULTS, "skipped": [],
                          "defaults": {**self.DEFAULTS["defaults"],
                                       "mythos": "claude-fable-5"}})
        self.assertEqual(result["defaults_failed"], {"mythos": "wrong-family"})
        self.assertNotIn("defaults_mismatched", result)
        self.assertTrue(any("nonsensical" in w for w in warnings), warnings)


class TestRound3Wording(_WeeklyLoop):
    """R3-4 (#203 probe round 3): the exact phrases, and the old ones gone."""

    def test_a_mismatch_says_does_not_match(self):
        out, _ = self._loop(lambda n: {"claude-sonnet-5": 500, "claude-opus-5": 300}, 1,
                            lambda k: self._docs(k, opus="claude-opus-6",
                                                 sonnet="claude-sonnet-5"))
        result = out[0]["result"]
        text = roster.render_summary(result) + "\n".join(out[0]["warnings"])
        self.assertIn("the CLI's default `claude-opus-6` for `opus` does not match this "
                      "run's catalogue (not-available)", text)
        self.assertNotIn("is not in this run's catalogue", text)
        self.assertNotIn("as with no default", text)

    def test_a_held_arm_says_none_retired(self):
        out, _ = self._loop(lambda n: {"claude-sonnet-5": 500, "claude-opus-5": 300}, 1,
                            lambda k: _failed_doc())
        result = out[0]["result"]
        why = self._reason(result, "claude-opus-5")
        self.assertTrue(why.endswith("held; none retired on a failed probe"), why)
        self.assertNotIn("no seat changes", json.dumps(result))
        summary = roster.render_summary(result)
        self.assertIn("none retired except models gone from the Models API", summary)
        self.assertNotIn("none retired, and none added but by the usage entry bar", summary)

    def test_the_workflow_probe_note_says_the_same(self):
        text = " ".join(EVAL_WORKFLOW.read_text(encoding="utf-8").split())
        self.assertIn("none retired except models gone from the Models API", text)
        self.assertNotIn("Their seats were held and none retired;", text)

    def test_the_docs_quote_the_new_phrases(self):
        adr = " ".join((REPO_ROOT / "docs" / "decisions"
                        / "0002-roster-follows-vendor-defaults.md").read_text(
                            encoding="utf-8").split())
        self.assertIn("held; none retired on a failed probe", adr)
        for rel in ("README.md", "DESIGN.md",
                    "docs/decisions/0002-roster-follows-vendor-defaults.md"):
            flat = " ".join((REPO_ROOT / rel).read_text(encoding="utf-8").split())
            with self.subTest(file=rel):
                self.assertIn("does not match this run's catalogue", flat)
                self.assertNotIn("is not in this run's catalogue", flat)
                self.assertNotIn("no seat changes on a failed probe", flat)


class TestEvalNoteKnowsTheOutcome(unittest.TestCase):
    """R3-3 (#203 probe round 3): the issue's eval sentence comes from the
    eval step's `outcome`, passed in through `env:`. The propose step runs
    BEFORE the badge/publish step, so a successful eval's sentence says the
    publish is the later step's and is not known here."""

    START = TestRosterOnlyDispatch.NOTE_START
    END = TestRosterOnlyDispatch.NOTE_END

    def setUp(self):
        doc = yaml.safe_load(EVAL_WORKFLOW.read_text(encoding="utf-8"))
        self.steps = doc["jobs"]["eval"]["steps"]
        self.by_name = {s.get("name"): s for s in self.steps}
        self.propose = self.by_name["Propose a roster change"]

    def _note(self, outcome, event=None):
        run = self.propose["run"]
        fragment = run[run.index(self.START):run.index(self.END)]
        tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
        (tmp / "event.json").write_text(json.dumps(event or {"schedule": "x"}),
                                        encoding="utf-8")
        env = {"PATH": os.environ.get("PATH", ""),
               "GITHUB_EVENT_PATH": str(tmp / "event.json")}
        if outcome is not None:
            env["EVAL_OUTCOME"] = outcome
        done = subprocess.run(["bash", "-c", "set -euo pipefail\n" + fragment
                               + '\nprintf "%s" "$eval_note"\n'],
                              capture_output=True, text=True, timeout=30, env=env)
        self.assertEqual(done.returncode, 0, done.stderr)
        return done.stdout

    def test_the_outcome_arrives_through_env_from_the_eval_steps_id(self):
        eval_step = self.by_name["Run the eval (both arms, judge)"]
        self.assertEqual(eval_step.get("id"), "eval")
        self.assertEqual(self.propose["env"]["EVAL_OUTCOME"], "${{ steps.eval.outcome }}")
        self.assertNotIn("${{", self.propose["run"])
        names = [s.get("name") for s in self.steps]
        self.assertLess(names.index("Propose a roster change"),
                        names.index("Build the badge over the run window, commit, and push"))

    @unittest.skipUnless(shutil.which("jq") and shutil.which("bash"), "needs jq and bash")
    def test_a_failed_eval_says_nothing_was_published(self):
        note = self._note("failure")
        self.assertIn("the eval step failed; nothing from this run was published to "
                      "`eval-results`", note)
        self.assertNotIn("are published", note)

    @unittest.skipUnless(shutil.which("jq") and shutil.which("bash"), "needs jq and bash")
    def test_a_successful_eval_says_publishing_is_the_next_step(self):
        note = self._note("success")
        self.assertIn("ran on the committed", note)
        self.assertIn("results are published to `eval-results` by the next step", note)
        self.assertNotIn("published to `eval-results` normally", note)

    @unittest.skipUnless(shutil.which("jq") and shutil.which("bash"), "needs jq and bash")
    def test_an_eval_that_did_not_run_says_so(self):
        for outcome in ("skipped", "cancelled", "", None):
            with self.subTest(outcome=outcome):
                note = self._note(outcome)
                self.assertIn("the eval step did not run; nothing from this run was "
                              "published to `eval-results`", note)
                self.assertNotIn("ran on the committed", note)

    @unittest.skipUnless(shutil.which("jq") and shutil.which("bash"), "needs jq and bash")
    def test_roster_only_wins(self):
        note = self._note("skipped", {"inputs": {"roster_only": True}})
        self.assertIn("no eval ran", note)
        self.assertNotIn("the eval step did not run", note)


class TestProposeStepGhWritesWarn(_ProposeStepFixture):
    """R3-5 (#203 probe round 3): every `gh issue` write in the propose step
    warns with a fixed `::warning::could not <verb> the roster tracking
    issue` and the step continues; `git push` of the proposal branch still
    fails the step."""

    DIFFERS = {"proposal": {"status": "differs", "changes": []}}

    @unittest.skipUnless(shutil.which("bash") and shutil.which("jq"), "needs bash and jq")
    def test_a_failed_close_warns_and_exits_zero(self):
        self._gh_fail = "issue close"
        out, calls, _ = self._run_step({"proposal": {"status": "same", "changes": []}},
                                       self._tracker())
        self.assertTrue(calls[0].startswith("issue close 7"), calls)
        self.assertIn("::warning::could not close the roster tracking issue\n", out)
        self.assertNotIn("closed the stale proposal issue", out)

    @unittest.skipUnless(shutil.which("bash") and shutil.which("jq"), "needs bash and jq")
    def test_a_failed_rejection_edit_warns_and_exits_zero(self):
        # No scripts/ in the step's working directory: rendering is rejected.
        self._gh_fail = "issue edit"
        out, calls, body = self._run_step(self.DIFFERS, self._tracker())
        self.assertTrue(calls[0].startswith("issue edit 7"), calls)
        self.assertIn("needs review", calls[0])
        self.assertIn("::warning::could not update the roster tracking issue\n", out)
        self.assertNotIn("updated the blocked proposal issue", out)

    @unittest.skipUnless(shutil.which("bash") and shutil.which("jq"), "needs bash and jq")
    def test_a_failed_rejection_create_warns_and_exits_zero(self):
        self._gh_fail = "issue create"
        out, calls, _ = self._run_step(self.DIFFERS, [])
        self.assertTrue(calls[0].startswith("issue create"), calls)
        self.assertIn("::warning::could not create the roster tracking issue\n", out)

    def test_every_gh_issue_write_is_guarded(self):
        """Structural, over the whole body: every `gh issue` command is an
        `if` condition or ends in `|| echo "::warning::could not ..."`."""
        lines = self.run_body.splitlines()
        commands = []
        i = 0
        while i < len(lines):
            stripped = lines[i].strip()
            if re.match(r"^(if )?gh issue ", stripped):
                command = stripped
                while command.endswith("\\"):
                    i += 1
                    command = command[:-1] + " " + lines[i].strip()
                commands.append(command)
            i += 1
        self.assertGreaterEqual(len(commands), 7, commands)
        for command in commands:
            with self.subTest(command=command[:40]):
                guarded = (command.startswith("if gh issue") or re.search(
                    r'\|\| echo "::warning::could not (close|update|create) the roster '
                    r'tracking issue"$', command))
                self.assertTrue(guarded, command)

    def test_git_push_still_fails_the_step(self):
        push = [ln.strip() for ln in self.run_body.splitlines()
                if "push --force-with-lease origin roster/proposal" in ln]
        self.assertEqual(len(push), 1, push)
        self.assertNotIn("||", push[0])
        readme = " ".join((REPO_ROOT / "README.md").read_text(encoding="utf-8").split())
        self.assertIn("a failed `gh issue` write in it is a fixed `::warning::`, never a "
                      "failed job, but a failed `git push` of `roster/proposal` still "
                      "fails it", readme)


class TestProposeStepDiffersBranchGhWrites(_ProposeStepFixture):
    """R3-5: the differs branch's final `gh issue` write, run for real
    against a throwaway git repository whose `origin` is a local bare repo
    created here (never a copy of this checkout, so nothing can reach a real
    remote)."""

    def _repo(self):
        origin = self.tmp / "origin.git"
        work = self.tmp / "work"
        git = ["git", "-c", "init.defaultBranch=main"]
        subprocess.run(git + ["init", "-q", "--bare", str(origin)], check=True)
        subprocess.run(git + ["init", "-q", str(work)], check=True)
        shutil.copytree(REPO_ROOT / "harness", work / "harness",
                        ignore=shutil.ignore_patterns("__pycache__"))
        (work / "scripts").mkdir()
        shutil.copy2(SCRIPTS_DIR / "render_roster_yaml.py", work / "scripts")
        (work / "evals").mkdir()
        shutil.copy2(REPO_ROOT / "evals" / "roster.yml", work / "evals")
        ident = ["-c", "user.name=t", "-c", "user.email=t@example.com"]
        subprocess.run(["git", "-C", str(work), "add", "-A"], check=True)
        subprocess.run(["git", "-C", str(work), *ident, "commit", "-q", "-m", "x"],
                       check=True)
        subprocess.run(["git", "-C", str(work), "remote", "add", "origin", str(origin)],
                       check=True)
        return work

    def _differs(self):
        committed = yaml.safe_load((REPO_ROOT / "evals" / "roster.yml").read_text(
            encoding="utf-8"))
        loop = _WeeklyLoop()
        out, _ = loop._loop(lambda n: {"claude-sonnet-5": 500, "claude-opus-5": 300,
                                       "claude-opus-5-5": 300}, 1,
                            lambda k: loop._docs(k), previous=committed)
        result = out[0]["result"]
        self.assertEqual(result["proposal"]["status"], "differs")
        return result

    @unittest.skipUnless(shutil.which("bash") and shutil.which("jq") and shutil.which("git"),
                         "needs bash, jq and git")
    def test_a_failed_final_create_and_edit_warn_and_exit_zero(self):
        latest = self._differs()
        work = self._repo()
        for fail, issues, verb in (("issue create", [], "create"),
                                   ("issue edit", self._tracker(), "update")):
            with self.subTest(fail=fail):
                self._gh_fail = fail
                (self.tmp / "gh.log").unlink(missing_ok=True)
                shutil.rmtree(self.tmp / "runner", ignore_errors=True)
                shutil.rmtree(self.tmp / "bin", ignore_errors=True)
                out, calls, _ = self._run_step(latest, issues, cwd=work)
                self.assertTrue(any("a change is proposed" in c for c in calls), calls)
                self.assertIn(f"::warning::could not {verb} the roster tracking issue\n",
                              out)


class TestHarnessVersionNonZeroExit(_ProbeFixture):
    """R3-7(a) (#203 probe round 3): `claude --version` printing a line and
    exiting non-zero gives a null `harness_version` and a warning."""

    def _fake(self):
        path = self.tmp / "claude-badversion"
        path.write_text(
            f"#!{sys.executable}\n"
            "import os, sys\n"
            "if '--version' in sys.argv:\n"
            "    print('9.9.9 (Claude Code)', flush=True)\n"
            "    sys.exit(3)\n"
            "os.environ['FAKE_INIT_MODE'] = 'simulate'\n"
            f"os.execv(sys.executable, [sys.executable, {str(FAKE_CLAUDE_INIT)!r}]"
            " + sys.argv[1:])\n", encoding="utf-8")
        path.chmod(0o755)
        return path

    def test_a_version_line_with_a_nonzero_exit_is_null_with_a_warning(self):
        import probe_model_defaults
        fake = self._fake()
        self.assertIsNone(probe_model_defaults.harness_version(str(fake), 30.0))
        done, doc = self._probe(fake, "--policy", str(self._policy(["opus"])))
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertIsNone(doc["harness_version"])
        self.assertIn("claude-opus-5-5", json.dumps(doc["defaults"]))
        self.assertIn("probe_model_defaults: warning: `claude --version` gave no usable "
                      "version line; harness_version is null", done.stderr)


# --- #203 probe round 4 -------------------------------------------------------


def _families(result):
    rungs = roster.tier_rungs(roster.load_policy(POLICY))
    return {roster.family_of(a["id"], rungs) for a in result["arms"]}


class TestMismatchFreezesInsteadOfAnEffectiveDefault(_WeeklyLoop):
    """R4-1 + R4-2 (#203 probe round 4), superseded by R7-1 (round 7): a
    CATALOGUE-MISMATCHED family FREEZES exactly like a probe failure —
    every listed previous arm holds its seat outright — rather than being
    decided on a guessed "effective default". With no previous arm listed,
    the family falls back to newest-in-tier when the enter window is not
    usable, and otherwise has no seat — as a clean run with the tier off the
    roster."""

    OPUS6 = _RosterFixture._model("claude-opus-6", "Claude Opus 6", "2026-09-27T00:00:00Z")

    def test_r4_s3_a_one_week_mismatch_matches_the_clean_run(self):
        # The reviewer's r4 s3.py: seated default opus-5-5 at ~1%, the
        # superseded opus-5 at ~41%; week 2 answers an unlisted opus-7.
        def usage(n):
            return {"claude-sonnet-5": 500, "claude-opus-5": 400,
                    "claude-opus-5-5": 10, "claude-haiku-4-5": 60}

        prev = dict(self.PREV0, arms=[{"id": "claude-sonnet-5"},
                                      {"id": "claude-opus-5-5"}])

        def clean(k):
            return self._docs(k, opus="claude-opus-5-5", sonnet="claude-sonnet-5",
                              haiku="claude-haiku-4-5")

        def docs(k):
            return (self._docs(k, opus="claude-opus-7", sonnet="claude-sonnet-5",
                               haiku="claude-haiku-4-5") if k == 2 else clean(k))

        base, _ = self._loop(usage, 5, clean, previous=prev)
        out, _ = self._loop(usage, 5, docs, previous=prev)
        expected = [["claude-sonnet-5", "claude-opus-5-5"]] * 5
        self.assertEqual([self._arms(w["result"]) for w in base], expected)
        self.assertEqual([self._arms(w["result"]) for w in out], expected)
        week2 = out[2]["result"]
        self.assertEqual(week2["defaults_mismatched"]["opus"]["class"], "not-available")
        self.assertNotIn("defaults_failed", week2)
        for week in out:
            self.assertEqual(week["result"]["retired_since_last"], [])
            self.assertEqual(week["result"]["added_since_last"], [])
        self.assertIn("held; none retired on a catalogue mismatch",
                      self._reason(week2, "claude-opus-5-5"))
        self.assertIn("no new seat on a catalogue mismatch while the family "
                      "holds a seat the Models API still lists",
                      self._reason(week2, "claude-opus-5", "excluded"))

    def test_r2_loop_a_a_persistent_mismatch_holds_the_listed_seat(self):
        # Round 2's loop.py A, updated for R7-1 (#203 probe round 7): the
        # CLI answers an unlisted opus every week from week 0. opus-5 (the
        # only previous arm `PREV0` lists) is frozen and holds the seat every
        # week; opus-5-5 (~30%-used, not a previous arm) earns none while
        # opus-5 remains listed (the governing guarantee wins over "a
        # persistent mismatch still seats the model the fleet uses").
        def usage(n):
            return {"claude-sonnet-5": 900, "claude-haiku-4-5": 50,
                    "claude-fable-5-1": 0, "claude-opus-5": 0,
                    "claude-opus-5-5": 400}

        out, _ = self._loop(usage, 6, lambda k: self._docs(
            k, opus="claude-opus-6", sonnet="claude-sonnet-5",
            haiku="claude-haiku-4-5"))
        weeks = [self._arms(w["result"]) for w in out]
        for k, arms in enumerate(weeks):
            self.assertIn("claude-opus-5", arms, k)
            self.assertNotIn("claude-opus-5-5", arms, k)
            self.assertEqual(out[k]["result"]["retired_since_last"], [], k)
            self.assertEqual(out[k]["result"]["added_since_last"], [], k)
        self.assertTrue(self._reason(out[0]["result"], "claude-opus-5").startswith(
            _mismatch_words("claude-opus-6", "opus", "not-available")))
        self.assertIn("no new seat on a catalogue mismatch while the family "
                      "holds a seat the Models API still lists",
                      self._reason(out[0]["result"], "claude-opus-5-5", "excluded"))

    def test_the_used_model_is_seated_once_no_previous_arm_of_the_family_is_listed(self):
        # Added for R5-2 (#203 probe round 5): the persistent mismatch
        # continues, but the listed arm (opus-5) then leaves the Models API
        # — the family holds no listed seat at all, so it falls back to
        # usage-qualified models and the heavily used opus-6 is seated.
        models_with_opus5 = self.BASE + [self.OPUS6]
        models_without_opus5 = [m for m in models_with_opus5
                                if m["id"] != "claude-opus-5"]

        def usage(n):
            return {"claude-sonnet-5": 900, "claude-opus-5": 0, "claude-opus-5-5": 0,
                    "claude-opus-6": 400}

        def docs(k):
            return self._docs(k, opus="claude-opus-7", sonnet="claude-sonnet-5")

        def models_for(k):
            return models_with_opus5 if k == 0 else models_without_opus5

        prev = copy.deepcopy(self.PREV0)
        out = []
        for k in range(2):
            now = self.START + timedelta(weeks=k, hours=12)
            counts: dict = {}
            for back in range(12, 0, -1):
                label = timeweeks.iso_week(now - timedelta(weeks=back))
                for model_id, n in usage(self._week_number(label)).items():
                    counts.setdefault(model_id, {})[label] = n
            census = {"generated_at": (self.START + timedelta(weeks=k, hours=6))
                      .strftime("%Y-%m-%dT%H:%M:%SZ"), "weeks": [], "counts": counts}
            result = roster.compute_roster(
                models_doc={"fetched_at": now.isoformat(), "models": models_for(k)},
                census_doc=census, policy=self._policy(), previous=copy.deepcopy(prev),
                now=now, warn=lambda _: None, defaults_doc=docs(k))
            out.append(result)
            if result["proposal"]["status"] == "differs":
                prev = yaml.safe_load(render_roster_yaml.render(result, "1", "abc"))
        self.assertIn("claude-opus-5", self._arms(out[0]))
        self.assertNotIn("claude-opus-6", self._arms(out[0]))
        self.assertIn("claude-opus-6", self._arms(out[1]))

    #: BASE plus an older sonnet no rule seats, so the judge is never an arm
    #: when the fallback seats every tier's newest.
    THIN_MODELS = _WeeklyLoop.BASE + [_RosterFixture._model(
        "claude-sonnet-4-6", "Claude Sonnet 4.6", "2025-11-24T00:00:00Z")]

    def _one(self, usage, docs, prev):
        now = self.START + timedelta(hours=12)
        counts: dict = {}
        for back in range(12, 0, -1):
            label = timeweeks.iso_week(now - timedelta(weeks=back))
            for model_id, n in usage(self._week_number(label)).items():
                counts.setdefault(model_id, {})[label] = n
        census = {"generated_at": (self.START + timedelta(hours=6))
                  .strftime("%Y-%m-%dT%H:%M:%SZ"), "weeks": [], "counts": counts}
        return roster.compute_roster(
            models_doc={"fetched_at": now.isoformat(), "models": list(self.THIN_MODELS)},
            census_doc=census, policy=self._policy(), previous=copy.deepcopy(prev),
            now=now, warn=lambda _: None, defaults_doc=docs)

    def test_r4_s2_s4_a_thin_enter_window_empties_no_family(self):
        # The reviewer's r4 s2.py / s4.py: the census is fresh, the enter
        # window is empty, the exit window is usable, and the previous
        # sonnet-5/opus-5 arms sit at 0%.
        prev = dict(self.PREV0, arms=[{"id": "claude-sonnet-5"}, {"id": "claude-opus-5"}])
        cases = {
            "s2": (lambda n: {"claude-sonnet-5": 100 if n <= 35 else 0,
                              "claude-haiku-4-5": 0, "claude-opus-5": 0},
                   dict(opus="claude-opus-9", sonnet="claude-sonnet-5"),
                   dict(opus="claude-opus-5-5", sonnet="claude-sonnet-5")),
            "s4": (lambda n: {"claude-haiku-4-5": 100 if n <= 35 else 0,
                              "claude-sonnet-5": 0, "claude-opus-5": 0},
                   dict(haiku="claude-haiku-9", sonnet="claude-sonnet-9",
                        opus="claude-opus-9", fable="claude-fable-9"),
                   dict(haiku="claude-haiku-4-5", sonnet="claude-sonnet-5",
                        opus="claude-opus-5-5", fable="claude-fable-5-1")),
        }
        for name, (usage, bad, good) in cases.items():
            with self.subTest(case=name):
                no_probe = self._one(usage, None, prev)
                result = self._one(usage, self._docs(0, **bad), prev)
                self.assertTrue(result["defaults_mismatched"])
                self.assertIsNotNone(result["source"]["census_at"])
                self.assertLessEqual(_families(no_probe), _families(result))
                out, _ = self._loop(usage, 3, lambda k: self._docs(
                    k, **(bad if k == 0 else good)), previous=prev,
                    models=self.THIN_MODELS)
                for k in range(1, 3):
                    before = out[k - 1]["result"]
                    after = out[k]["result"]
                    added = {a["id"] for a in before["added_since_last"]}
                    retired = {r["id"] for r in before["retired_since_last"]}
                    self.assertFalse(added & {r["id"] for r in after["retired_since_last"]},
                                     (k, added))
                    self.assertFalse(retired & {a["id"] for a in after["added_since_last"]},
                                     (k, retired))

    def test_no_candidate_with_a_usable_enter_window_has_no_seat(self):
        # Nothing of the family is a listed previous arm or clears the bar:
        # the same as a clean run with the tier off the roster.
        def usage(n):
            return {"claude-sonnet-5": 900, "claude-opus-5": 0, "claude-opus-5-5": 0}

        prev = dict(self.PREV0, arms=[{"id": "claude-sonnet-5"}])
        clean, _ = self._loop(usage, 1, lambda k: self._docs(
            k, opus="claude-opus-5-5", sonnet="claude-sonnet-5"), previous=prev)
        out, _ = self._loop(usage, 1, lambda k: self._docs(
            k, opus="claude-opus-9", sonnet="claude-sonnet-5"), previous=prev)
        result = out[0]["result"]
        self.assertEqual(self._arms(result), self._arms(clean[0]["result"]))
        self.assertNotIn("opus", _families(result))
        said = _mismatch_words("claude-opus-9", "opus", "not-available")
        self.assertIn(said, self._reason(result, "claude-opus-5-5", "excluded"))


class TestFrozenFallbackKeysOnTheEnterWindow(_WeeklyLoop):
    """R4-3 (#203 probe round 4): R3-6's fallback keys on the ENTER window,
    not on the census as a whole — a fresh census whose enter window is under
    the floors still falls back to newest-in-tier for a frozen family with
    nothing listed."""

    MODELS = [_RosterFixture._model("claude-haiku-5", "H5", "2026-09-01T00:00:00Z"),
              _RosterFixture._model("claude-sonnet-6", "S6", "2026-09-01T00:00:00Z"),
              # Not the newest opus, so never seated: the judge.
              _RosterFixture._model("claude-opus-5-9", "O59", "2026-08-01T00:00:00Z"),
              _RosterFixture._model("claude-opus-6", "O6", "2026-09-01T00:00:00Z")]

    def test_a_fresh_census_with_a_thin_enter_window_falls_back(self):
        def usage(n):
            return {"claude-sonnet-6": 100 if n <= 35 else 0}

        no_probe, _ = self._loop(usage, 1, lambda k: None, models=self.MODELS)
        out, _ = self._loop(usage, 1, lambda k: _failed_doc(), models=self.MODELS)
        result = out[0]["result"]
        self.assertIsNotNone(result["source"]["census_at"])
        self.assertIn("opus", result["defaults_failed"])
        self.assertEqual(self._arms(result), self._arms(no_probe[0]["result"]))
        self.assertIn("claude-opus-6", self._arms(result))
        self.assertIn("falls back to newest per tier as with no probe",
                      self._reason(result, "claude-opus-6"))

    def test_the_docs_say_enter_window(self):
        for rel in ("README.md", "DESIGN.md", "evals/roster-policy.yml",
                    "docs/decisions/0002-roster-follows-vendor-defaults.md"):
            flat = " ".join((REPO_ROOT / rel).read_text(encoding="utf-8").split())
            flat = re.sub(r"\s*#\s*", " ", flat)
            with self.subTest(file=rel):
                self.assertIn("no usable enter window", flat)
                self.assertNotIn("no usable census, as the newest", flat)
                self.assertNotIn("With no usable census and no seat", flat)


class TestFrozenFallbackMutants(_RosterFixture):
    """R4-4 (#203 probe round 4): the three mutants round 4 left alive."""

    NOW5 = TestFrozenFamilyFallsBackWithNoCensus.NOW5
    PREV = TestFrozenFamilyFallsBackWithNoCensus.PREV

    def _run(self, models, defaults, policy=None):
        return roster.compute_roster(
            models_doc={"fetched_at": self.NOW5.isoformat(), "models": models},
            census_doc=None, policy=policy or self._policy(),
            previous=copy.deepcopy(self.PREV), now=self.NOW5, warn=lambda _: None,
            defaults_doc=defaults)

    def test_a_only_the_newest_of_a_frozen_family_is_seated(self):
        models = [self._model("claude-sonnet-6", "S6", "2026-09-01T00:00:00Z"),
                  self._model("claude-opus-5-9", "O59", "2026-08-01T00:00:00Z"),
                  self._model("claude-opus-6", "O6", "2026-09-01T00:00:00Z")]
        no_probe = self._run(models, None)
        failed = self._run(models, _failed_doc())
        self.assertEqual(self._arms(failed), self._arms(no_probe))
        self.assertIn("claude-opus-6", self._arms(failed))
        self.assertNotIn("claude-opus-5-9", self._arms(failed))

    def test_b_a_held_snapshot_on_its_collapsed_alias_blocks_a_usage_seat(self):
        # The previous arm is the dated opus-5 snapshot; the catalogue lists
        # its undated alias too, so the family still holds a listed seat and
        # a heavily used opus-5-5 is NOT seated on the failed probe.
        models = self._models_doc(extra=[self._model(
            "claude-opus-5-20260401", "Claude Opus 5", "2026-04-01T00:00:00Z")])
        previous = {**self.PREVIOUS, "arms": [{"id": "claude-sonnet-5"},
                                              {"id": "claude-opus-5-20260401"}]}
        census = self._census(extra={"claude-opus-5-5": {w: 452 for w in self.ENTER}})
        doc = {**self.DEFAULTS, "defaults": {"sonnet": "claude-sonnet-5"},
               "errors": {"opus": "timeout"}}
        result, _ = self._compute(defaults=doc, previous=previous, models=models,
                                  census=census)
        self.assertIn("claude-opus-5", self._arms(result))
        self.assertNotIn("claude-opus-5-5", self._arms(result))
        self.assertIn("while the family holds a seat the Models API still lists",
                      self._reason(result, "claude-opus-5-5", "excluded"))

    def test_c_a_positive_cooling_off_is_honoured_as_with_no_probe(self):
        policy = self._policy(cooling_off_days=7)
        models = [self._model("claude-sonnet-6", "S6", "2026-09-01T00:00:00Z"),
                  self._model("claude-opus-5-9", "O59", "2026-08-01T00:00:00Z"),
                  self._model("claude-opus-6", "O6", "2026-10-03T00:00:00Z")]
        no_probe = self._run(models, None, policy)
        failed = self._run(models, _failed_doc(), policy)
        self.assertEqual(self._arms(failed), self._arms(no_probe))
        self.assertNotIn("claude-opus-6", self._arms(failed))


class TestRound4Docs(unittest.TestCase):
    """R4-5 (#203 probe round 4): docs accuracy."""

    ADR = REPO_ROOT / "docs" / "decisions" / "0002-roster-follows-vendor-defaults.md"

    def _flat(self, path):
        return " ".join(path.read_text(encoding="utf-8").split())

    def test_a_the_frozen_zero_default_case_is_a_clean_runs_outcome(self):
        self.assertIn("the same outcome a clean run gives", self._flat(self.ADR))
        for rel in ("README.md", "DESIGN.md", "HANDOFF.md", "evals/roster-policy.yml",
                    "docs/decisions/0002-roster-follows-vendor-defaults.md",
                    "harness/roster.py", ".github/workflows/eval.yml"):
            with self.subTest(file=rel):
                self.assertNotIn("clean probe next week seats",
                                 self._flat(REPO_ROOT / rel))

    def test_b_a_freeze_usage_seat_can_outlast_the_freeze(self):
        flat = self._flat(self.ADR)
        self.assertIn("can outlast the freeze", flat)
        self.assertIn("`superseded_exit_weeks` buffer", flat)

    def test_c_the_success_sentence_covers_a_skipped_publish(self):
        doc = yaml.safe_load(EVAL_WORKFLOW.read_text(encoding="utf-8"))
        propose = next(s for s in doc["jobs"]["eval"]["steps"]
                       if s.get("name") == "Propose a roster change")
        line = next(ln for ln in propose["run"].splitlines()
                    if "by the next step" in ln)
        self.assertIn("if that step failed or was skipped", line)


# --- #203 probe round 5 -------------------------------------------------------


class TestNoCreatedAtIsAProbeFailure(_WeeklyLoop):
    """R5-1 (#203 probe round 5): `no-created-at` (the vendor default the
    CLI names is listed but has no `created_at`) is a PROBE FAILURE, not a
    catalogue mismatch — the family freezes (F1/F2, #203 probe round 1),
    exactly as a wrong-tier or wrong-family answer does (R3-2). Without the
    freeze, a one-week loss of `created_at` retired a seat a clean run would
    have kept — the reviewer's p1.py."""

    @staticmethod
    def _usage(n):
        # Fleet still mostly on opus-5 (~42%), the vendor's newer default
        # opus-5-5 already carrying a small usage share of its own.
        return {"claude-sonnet-5": 500, "claude-opus-5": 400, "claude-opus-5-5": 5}

    def _no_created_at(self, k):
        models = [dict(m) for m in self.BASE]
        for m in models:
            if m["id"] == "claude-opus-5-5":
                m["created_at"] = None
        return models

    def test_p1_a_one_week_loss_of_created_at_changes_no_opus_seat(self):
        clean = self._docs
        base, _ = self._loop(self._usage, 4, clean)

        def docs_and_models(k):
            return clean(k)

        # Week 1's Models API drops opus-5-5's created_at; every other week
        # is clean.
        def loop_with_nca():
            prev = copy.deepcopy(self.PREV0)
            out = []
            for k in range(4):
                now = self.START + timedelta(weeks=k, hours=12)
                counts: dict = {}
                for back in range(12, 0, -1):
                    label = timeweeks.iso_week(now - timedelta(weeks=back))
                    for model_id, n in self._usage(self._week_number(label)).items():
                        counts.setdefault(model_id, {})[label] = n
                census = {"generated_at": (self.START + timedelta(weeks=k, hours=6))
                          .strftime("%Y-%m-%dT%H:%M:%SZ"), "weeks": [], "counts": counts}
                models = self._no_created_at(k) if k == 1 else list(self.BASE)
                warnings: list[str] = []
                result = roster.compute_roster(
                    models_doc={"fetched_at": now.isoformat(), "models": models},
                    census_doc=census, policy=self._policy(), previous=copy.deepcopy(prev),
                    now=now, warn=warnings.append, defaults_doc=clean(k))
                out.append({"result": result, "warnings": warnings})
                if result["proposal"]["status"] == "differs":
                    prev = yaml.safe_load(render_roster_yaml.render(result, "1", "abc"))
            return out

        out = loop_with_nca()
        self.assertEqual([sorted(self._arms(w["result"])) for w in out],
                         [sorted(self._arms(w["result"])) for w in base])
        week1 = out[1]["result"]
        self.assertEqual(week1["defaults_failed"], {"opus": "no-created-at"})
        self.assertNotIn("defaults_mismatched", week1)
        self.assertEqual(week1["retired_since_last"], [])
        self.assertEqual(week1["added_since_last"], [])
        self.assertEqual(
            self._reason(week1, "claude-opus-5-5"),
            "vendor default for `opus` unknown this run (probe: "
            "no-created-at); held; none retired on a failed probe")
        # The next week probes cleanly and decides as usual: nothing carried.
        self.assertNotIn("defaults_failed", out[2]["result"])

    def test_the_two_classes_still_match_the_defaults_error_re(self):
        for cls in (roster.UNRESOLVED_NO_CREATED_AT, roster.UNRESOLVED_WRONG_TIER):
            with self.subTest(cls=cls):
                self.assertTrue(roster.DEFAULTS_ERROR_RE.match(cls))



class TestPreviousArmHeldUnderItsDatedId(_RosterFixture):
    """R5-3 (#203 probe round 5): `_default_rung_decision` treats a model as
    a previous arm if it is literally in `previous_arms` OR it is the alias
    of a dated snapshot id in `previous_arms` — so a superseded arm
    published under its dated id still gets the `superseded_exit_weeks`
    buffer once its undated alias appears in the catalogue too, rather than
    retiring on sight — the reviewer's p3.py."""

    def test_a_superseded_arm_held_only_under_its_dated_id_keeps_its_buffer(self):
        extra = [self._model("claude-opus-5-20260401", "Claude Opus 5",
                             "2026-04-01T00:00:00Z")]
        models = self._models_doc(extra=extra)
        prev = {**self.PREVIOUS, "arms": [{"id": "claude-sonnet-5"},
                                          {"id": "claude-opus-5-20260401"},
                                          {"id": "claude-opus-5-5"}]}
        result, _ = self._compute(defaults=self.DEFAULTS, previous=prev, models=models)
        self.assertIn("claude-opus-5", self._arms(result))
        self.assertIn("inside its 1-week buffer",
                      self._reason(result, "claude-opus-5"))
        # The dated arm's own retirement is the alias collapse, not a real
        # loss: opus-5 (undated) now holds the seat.
        ret = self._reason(result, "claude-opus-5-20260401", "retired_since_last")
        self.assertIn("which holds the seat", ret)

    def test_retired_since_last_claims_the_alias_holds_the_seat_only_if_it_does(self):
        # When the undated alias does NOT end up seated this run (its own
        # buffer has expired and its usage is below the exit bar, so it
        # retires too), the dated snapshot's retirement must not falsely
        # claim the alias "holds the seat".
        extra = [self._model("claude-opus-5-20260401", "Claude Opus 5",
                             "2026-04-01T00:00:00Z")]
        models = self._models_doc(extra=extra)
        prev = {**self.PREVIOUS, "arms": [{"id": "claude-sonnet-5"},
                                          {"id": "claude-opus-5-20260401"},
                                          {"id": "claude-opus-5-5"}]}
        census = self._later_census(opus5_w40=0, opus55_w40=0)
        result, _ = self._compute(defaults=self.DEFAULTS, previous=prev, models=models,
                                  census=census, now=self.LATER)
        self.assertNotIn("claude-opus-5", self._arms(result))
        ret = self._reason(result, "claude-opus-5-20260401", "retired_since_last")
        self.assertNotIn("which holds the seat", ret)
        self.assertIn("below the", ret)


class TestR8DatedIdNewerThanDefault(_RosterFixture):
    """R8-2 (#203 probe round 8): `_default_rung_decision`'s newer-than-
    default branch checked literal `previous_arms` rather than the dated-
    id-collapsing `held_arm_ids` every other branch in the function uses,
    so a previous arm published only under its DATED id got no exit check
    at all and was silently excluded, while the identical arm under its
    undated form was correctly held. The reviewer's e1.py."""

    def test_a_dated_previous_arm_newer_than_default_is_held_like_the_undated_form(self):
        extra = [self._model("claude-opus-6", "Claude Opus 6", "2026-09-27T00:00:00Z"),
                 self._model("claude-opus-6-20260927", "Claude Opus 6",
                            "2026-09-27T00:00:00Z")]
        models = self._models_doc(extra=extra)
        census = self._census(extra={"claude-opus-6-20260927":
                                     {w: 200 for w in self.ENTER}})
        for label, prevarm in (("dated", "claude-opus-6-20260927"),
                               ("undated", "claude-opus-6")):
            with self.subTest(label=label):
                prev = {**self.PREVIOUS,
                       "arms": self.PREVIOUS["arms"] + [{"id": prevarm}]}
                result, _ = self._compute(defaults=self.DEFAULTS, models=models,
                                          census=census, previous=prev)
                self.assertIn("claude-opus-6", self._arms(result))
                why = self._reason(result, "claude-opus-6")
                self.assertIn("newer than the vendor default `claude-opus-5-5`", why)


class TestR8SeatedInTierDatedId(_RosterFixture):
    """R8-3(a) (#203 probe round 8): `compute_roster`'s tier-on-roster check
    for a deferred default (`seated_in_tier`) compared each previous arm id
    LITERALLY against `seated_ids`, never folding it through `snapshots`
    first — so a peer previous arm seated this run under its undated alias,
    but held in the committed roster only under its dated id, made the
    tier look empty of any other seated previous arm and the default got
    no seat at all. The reviewer's e2.py (E3)."""

    def test_a_dated_previous_peer_still_seats_the_tier_default(self):
        census = self._census()
        census["counts"]["claude-opus-5"] = {w: 50 for w in self.ENTER}
        census["counts"]["claude-sonnet-5"] = {w: 850 for w in self.ENTER}
        models = self._models_doc(extra=[self._model(
            "claude-opus-5-20260401", "Claude Opus 5", "2026-04-01T00:00:00Z")])
        for label, prevarm in (("dated", "claude-opus-5-20260401"),
                               ("undated", "claude-opus-5")):
            with self.subTest(label=label):
                prev = {**self.PREVIOUS, "arms": [{"id": "claude-sonnet-5"},
                                                  {"id": prevarm}]}
                result, _ = self._compute(defaults=self.DEFAULTS, models=models,
                                          previous=prev, census=census)
                self.assertIn("claude-opus-5-5", self._arms(result))
                self.assertIn("the tier is on the roster because previous arm",
                              self._reason(result, "claude-opus-5-5"))


class TestR8GenericPathDatedId(_RosterFixture):
    """R8-3(b) (#203 probe round 8): the no-default generic path
    (`if reason is None and model_id in previous_arms: holdover(...)`)
    also checked literal `previous_arms` rather than the collapsed held
    set, so a family with no vendor default (haiku here) held a previous
    arm published under its undated id but silently dropped the identical
    arm published only under its dated id. The reviewer's e2.py (E2)."""

    def test_a_dated_previous_arm_in_a_no_default_tier_is_still_held(self):
        models = self._models_doc(extra=[self._model(
            "claude-haiku-4-5-20251001", "Claude Haiku 4.5", "2025-10-01T00:00:00Z")])
        for label, prevarm in (("dated", "claude-haiku-4-5-20251001"),
                               ("undated", "claude-haiku-4-5")):
            with self.subTest(label=label):
                prev = {**self.PREVIOUS,
                       "arms": self.PREVIOUS["arms"] + [{"id": prevarm}],
                       "preflight": {"id": "claude-haiku-4-5"}}
                result, _ = self._compute(defaults=self.DEFAULTS, models=models,
                                          previous=prev)
                self.assertIn("claude-haiku-4-5", self._arms(result))


class TestR10SeatedInTierWordingNamesTheRename(_RosterFixture):
    """N3 (adversarial round 10): when `seated_in_tier`'s previous arm is
    held under a RENAMED spelling — the previous roster's own id
    (`claude-opus-5`) is not what this run's catalogue lists; `_seated_form`
    maps it onto the dated snapshot that is (`claude-opus-5-20260401`) — the
    default's "the tier is on the roster because previous arm `X`" reason
    named the renamed form `X` a "previous arm", which the previous roster
    never called it by that spelling. The reviewer's c4.py."""

    def test_the_reason_names_both_the_seated_form_and_the_previous_arm(self):
        models = self._models_doc(
            drop=["claude-opus-5"],
            extra=[self._model("claude-opus-5-20260401", "Claude Opus 5",
                               "2026-04-01T00:00:00Z")])
        census = self._census(extra={"claude-opus-5": {w: 50 for w in self.ENTER}})
        previous = {**self.PREVIOUS, "arms": [{"id": "claude-sonnet-5"},
                                              {"id": "claude-opus-5"}]}
        result, _ = self._compute(defaults=self.DEFAULTS, models=models,
                                  census=census, previous=previous)
        self.assertIn("claude-opus-5-20260401", self._arms(result))
        why = self._reason(result, "claude-opus-5-5")
        self.assertIn("the tier is on the roster because", why)
        self.assertIn("`claude-opus-5-20260401` (previous arm `claude-opus-5`) "
                      "is in it and still seated", why)
        self.assertNotIn("previous arm `claude-opus-5-20260401`", why)


class TestMismatchCandidateSurvivingMutants(_RosterFixture):
    """R5-4 (#203 probe round 5): three mutants that survived round 4's
    mutation pass. Round 4's candidate-selection machinery they targeted is
    gone (R7-1, #203 probe round 7 — a mismatch freezes exactly like a
    probe failure now), but the edge cases they pin — a share exactly at
    the entry bar, a listed arm held only under its dated id, and a
    `created_at`-less model that must not raise — are still real, so the
    tests are converted to the freeze behavior rather than deleted."""

    def test_a_share_exactly_at_the_entry_bar_qualifies_with_no_listed_arm(self):
        # (a): no previous arm of the family is listed, so candidates come
        # from usage alone; a share exactly at `arm_enter_usage_pct` must
        # qualify (`>=`, not `>`).
        models = self._models_doc(drop=("claude-opus-5", "claude-opus-5-5"),
                                  extra=[self._model("claude-opus-6", "O6",
                                                     "2026-09-01T00:00:00Z")])
        weeks = ["2026-W36", "2026-W37", "2026-W38", "2026-W39"]
        # Exactly 10.0% over the 4-week enter window.
        census = {"generated_at": "2026-09-27T06:00:00Z", "weeks": [], "counts": {
            "claude-sonnet-5": {w: 900 for w in weeks},
            "claude-opus-6": {w: 100 for w in weeks}}}
        prev = {**self.PREVIOUS, "arms": [{"id": "claude-sonnet-5"}]}
        doc = {**self.DEFAULTS, "defaults": {"opus": "claude-opus-9",
                                             "sonnet": "claude-sonnet-5"}}
        result, _ = self._compute(defaults=doc, previous=prev, models=models,
                                  census=census)
        self.assertIn("claude-opus-6", self._arms(result))

    def test_b_the_dated_alias_of_a_listed_arm_is_a_held_candidate(self):
        # (b): the listed previous arm is published under its DATED id
        # only, and carries too little usage to qualify on its own; a
        # much newer, heavily used peer (opus-6) must still get NO seat —
        # `holds_listed_seat` sees the listed arm via the dated-alias
        # collapse (`frozen_held_ids`), not just literal ids. Without the
        # alias collapse, the dated id is not in `available` at all, the
        # family looks like it holds no seat, and opus-6 would wrongly
        # qualify by usage instead.
        extra = [self._model("claude-opus-5-20260401", "Claude Opus 5",
                             "2026-04-01T00:00:00Z"),
                 self._model("claude-opus-6", "Claude Opus 6",
                            "2026-09-20T00:00:00Z")]
        models = self._models_doc(extra=extra)
        prev = {**self.PREVIOUS, "arms": [{"id": "claude-sonnet-5"},
                                          {"id": "claude-opus-5-20260401"}]}
        weeks = ["2026-W36", "2026-W37", "2026-W38", "2026-W39"]
        census = {"generated_at": "2026-09-27T06:00:00Z", "weeks": [], "counts": {
            "claude-sonnet-5": {w: 500 for w in weeks},
            "claude-opus-5": {w: 5 for w in weeks},
            "claude-opus-6": {w: 400 for w in weeks}}}
        doc = {**self.DEFAULTS, "defaults": {"opus": "claude-opus-9",
                                             "sonnet": "claude-sonnet-5"}}
        result, _ = self._compute(defaults=doc, previous=prev, models=models,
                                  census=census)
        self.assertIn("claude-opus-5", self._arms(result))
        self.assertNotIn("claude-opus-6", self._arms(result))
        self.assertIn("no new seat on a catalogue mismatch while the family "
                      "holds a seat the Models API still lists",
                      self._reason(result, "claude-opus-6", "excluded"))

    def test_c_a_mismatched_model_with_no_created_at_does_not_raise(self):
        # (c): the freeze branch holds a listed arm outright, with no need
        # to read `created_at` at all — a listed arm lacking one (`claude-
        # opus-6`) and another (`claude-opus-7`) must not raise, and both
        # are simply held.
        opus6 = self._model("claude-opus-6", "Claude Opus 6", None)
        opus7 = self._model("claude-opus-7", "Claude Opus 7", None)
        models = self._models_doc(extra=[opus6, opus7],
                                  drop=("claude-opus-5", "claude-opus-5-5"))
        prev = {**self.PREVIOUS, "arms": [{"id": "claude-sonnet-5"},
                                          {"id": "claude-opus-6"},
                                          {"id": "claude-opus-7"}]}
        doc = {**self.DEFAULTS, "defaults": {"opus": "claude-opus-9",
                                             "sonnet": "claude-sonnet-5"}}
        result, _ = self._compute(defaults=doc, previous=prev, models=models)
        self.assertIn("claude-opus-7", self._arms(result))
        self.assertIn("claude-opus-6", self._arms(result))
        # #203 round 7: the freeze holds every listed previous arm outright
        # on a catalogue mismatch — no `created_at`, no buffer, no
        # exception — exactly as it does on a failed probe.
        self.assertIn("held; none retired on a catalogue mismatch",
                      self._reason(result, "claude-opus-6"))
        self.assertIn("held; none retired on a catalogue mismatch",
                      self._reason(result, "claude-opus-7"))


class TestMismatchWeekRetiresNothing(_WeeklyLoop):
    """R6-1 (#203 probe round 6), superseded by R7-1 (round 7): a
    catalogue-mismatch week freezes its family exactly like a probe
    failure — every listed previous arm is held outright, no exit check at
    all — so a single mismatch week must not retire a listed previous arm
    even when a real exit check that week would (opus-5 here, well under
    the exit bar): the arm holds its seat every week, mismatch or not,
    identically to a run with no mismatch at all. The reviewer's
    adv203-probe-r6 f1.py, run with the `_WeeklyLoop` week-by-week loop."""

    MODELS = [
        _RosterFixture._model("claude-haiku-4-5", "Claude Haiku 4.5", "2025-10-01T00:00:00Z"),
        _RosterFixture._model("claude-sonnet-5", "Claude Sonnet 5", "2026-02-01T00:00:00Z"),
        _RosterFixture._model("claude-opus-5", "Claude Opus 5", "2026-04-01T00:00:00Z"),
        _RosterFixture._model("claude-opus-5-5", "Claude Opus 5.5", "2026-06-01T00:00:00Z"),
        _RosterFixture._model("claude-fable-5-1", "Claude Fable 5.1", "2026-09-01T00:00:00Z"),
    ]
    BAD_DEFAULT = "claude-opus-6"  # Not in MODELS: every "mm" week is a
                                    # catalogue mismatch (probe: not-available).

    @staticmethod
    def _usage(n):
        # opus-5 well under the 2% exit bar (0.5%), opus-5-5 dominant —
        # the shape from the reproduction: a real exit check on opus-5
        # would retire it, so only a mismatch's own carve-out can save it.
        return {"claude-sonnet-5": 500, "claude-haiku-4-5": 50,
                "claude-fable-5-1": 0, "claude-opus-5": 5,
                "claude-opus-5-5": 400}

    def _docs_with(self, mismatch_weeks):
        def docs_for(k):
            d = self._docs(k, opus="claude-opus-5", sonnet="claude-sonnet-5")
            if k in mismatch_weeks:
                d["defaults"]["opus"] = self.BAD_DEFAULT
            return d
        return docs_for

    def test_a_mismatch_week_changes_nothing_a_clean_week_would_not_change(self):
        previous = {**self.PREV0,
                    "arms": [{"id": "claude-sonnet-5"}, {"id": "claude-opus-5"},
                            {"id": "claude-opus-5-5"}]}
        clean_out, _ = self._loop(self._usage, 4, self._docs_with(set()),
                                  previous=previous, models=self.MODELS)
        mismatch_out, _ = self._loop(self._usage, 4, self._docs_with({1}),
                                     previous=previous, models=self.MODELS)
        clean_arms = [sorted(self._arms(w["result"])) for w in clean_out]
        mismatch_arms = [sorted(self._arms(w["result"])) for w in mismatch_out]
        self.assertEqual(clean_arms, mismatch_arms)
        for week in clean_out + mismatch_out:
            self.assertEqual(week["result"].get("retired_since_last", []), [])
        # claude-opus-5 keeps its seat every week of the mismatch run too.
        for week in mismatch_out:
            self.assertIn("claude-opus-5", self._arms(week["result"]))


class TestRound5Docs(unittest.TestCase):
    """R5-5 (#203 probe round 5): docs accuracy."""

    ADR = REPO_ROOT / "docs" / "decisions" / "0002-roster-follows-vendor-defaults.md"

    def _flat(self, path):
        return " ".join(path.read_text(encoding="utf-8").split())

    def test_no_created_at_is_listed_as_a_failure_everywhere(self):
        for rel in ("README.md", "DESIGN.md", "evals/roster-policy.yml",
                    "docs/decisions/0002-roster-follows-vendor-defaults.md",
                    "harness/roster.py"):
            flat = self._flat(REPO_ROOT / rel)
            with self.subTest(file=rel):
                self.assertNotIn(
                    "not available, an ambiguous snapshot, no created_at", flat)

    def test_the_governing_guarantee_is_stated_in_the_adr_and_class_docstring(self):
        flat = self._flat(self.ADR)
        self.assertIn("changes no seat", flat)
        roster_flat = self._flat(REPO_ROOT / "harness" / "roster.py")
        self.assertIn("changes no seat", roster_flat)


# --- #203 probe round 7 -------------------------------------------------------


class TestRound7ProbeReproductions(_WeeklyLoop):
    """R7-1 + R7-2 (#203 probe round 7): the reviewer's own reproductions,
    each RED on HEAD f7e0ca8 — the effective-default machinery that round 7
    deleted retired or excluded a listed seat a clean week keeps, through a
    different branch each time; R7-2 is a plain clean-run bug, unrelated to
    a mismatch. Verified red against f7e0ca8's `harness/roster.py` loaded as
    its own module (never checked out into this working tree) before this
    class was written; the failure each docstring names is what that run
    showed."""

    def test_g2_a_ramping_family_holds_its_seat_through_one_mismatch_week(self):
        # g2.py: opus-5 carries no usage before week 39, then a steady 0.5%
        # — never above the 2% exit bar. On f7e0ca8, the mismatch week ran
        # opus-5 straight through the EFFECTIVE default's "seated or held on
        # the tier's combined share" exit check and retired it on the spot
        # (`retired_since_last == [{'id': 'claude-opus-5', ...}]`, arms ==
        # `['claude-sonnet-5']`) — a seat the same week's CLEAN run (vendor
        # default opus-5-5, opus-5 superseded but inside its buffer) does
        # NOT retire. The freeze must retire no more than a clean week does
        # that same week: nothing.
        def usage(n):
            return {"claude-sonnet-5": 1000, "claude-haiku-4-5": 50,
                    "claude-fable-5-1": 0,
                    "claude-opus-5": 5 if n >= 39 else 0,
                    "claude-opus-5-5": 0}

        def clean(k):
            return self._docs(k)

        def mismatch(k):
            d = self._docs(k)
            if k == 0:
                d["defaults"]["opus"] = "claude-opus-6"
            return d

        base, _ = self._loop(usage, 6, clean)
        out, _ = self._loop(usage, 6, mismatch)
        week0 = out[0]["result"]
        self.assertEqual(week0["retired_since_last"], [])
        self.assertIn("claude-opus-5", self._arms(week0))
        self.assertIn("held; none retired on a catalogue mismatch",
                      self._reason(week0, "claude-opus-5"))
        # From the week after the mismatch on, the two runs agree exactly —
        # the family was never dropped by the one mismatch week.
        self.assertEqual([self._arms(w["result"]) for w in out[1:]],
                         [self._arms(w["result"]) for w in base[1:]])

    def test_g3_a_family_held_only_under_its_dated_id_survives_a_mismatch(self):
        # g3.py: the family's only listed arm is published under its DATED
        # id, at 5.5% usage (between the 2% exit and 10% entry bars). On
        # f7e0ca8, the mismatch week retired it outright
        # (`retired_since_last == [{'id': 'claude-opus-5-20260401', ...}]`,
        # arms == `['claude-sonnet-5']`) and NEVER RECOVERED — every later
        # clean week still disagreed with the all-clean run
        # (`weeks1..3 equal: False` in the reproduction). The freeze must
        # hold it, and every week after the mismatch must match the
        # all-clean run exactly.
        M = self._model
        MODELS = list(self.BASE) + [M("claude-opus-5-20260401", "Claude Opus 5",
                                      "2026-04-01T00:00:00Z")]
        PREV = dict(self.PREV0, arms=[{"id": "claude-sonnet-5"},
                                      {"id": "claude-opus-5-20260401"}])

        def usage(n):
            return {"claude-sonnet-5": 1000, "claude-haiku-4-5": 50,
                    "claude-fable-5-1": 0, "claude-opus-5": 55,
                    "claude-opus-5-5": 0}

        def clean(k):
            return self._docs(k)

        def mismatch(k):
            d = self._docs(k)
            if k == 0:
                d["defaults"]["opus"] = "claude-opus-6"
            return d

        base, _ = self._loop(usage, 4, clean, previous=PREV, models=MODELS)
        out, _ = self._loop(usage, 4, mismatch, previous=PREV, models=MODELS)
        week0 = out[0]["result"]
        # The dated snapshot's own retirement is the alias collapse, not a
        # real loss (its undated alias holds the seat instead); no OTHER
        # retirement happens.
        self.assertEqual([r["id"] for r in week0["retired_since_last"]],
                         ["claude-opus-5-20260401"])
        self.assertIn("which holds the seat",
                      self._reason(week0, "claude-opus-5-20260401", "retired_since_last"))
        self.assertIn("claude-opus-5", self._arms(week0))
        self.assertIn("held; none retired on a catalogue mismatch",
                      self._reason(week0, "claude-opus-5"))
        self.assertEqual([self._arms(w["result"]) for w in out[1:]],
                         [self._arms(w["result"]) for w in base[1:]])

    def test_g4_a_seated_default_held_only_under_its_dated_id_at_5_percent(self):
        # g4.py: a CLEAN run (no mismatch at all) — the vendor default names
        # the alias `claude-opus-5` directly, and the only previous arm of
        # that family is listed under its dated snapshot
        # `claude-opus-5-20260401`. `_default_rung_decision`'s
        # `model_id == default_id` branch checked `model_id in
        # previous_arms` literally, which the dated form never satisfies, so
        # on f7e0ca8 this genuine clean-run bug (R7-2) fell through to "the
        # tier is not on the roster" and excluded it even at 5% usage
        # (above the 2% exit bar) — `arms == ['claude-sonnet-5']`. Fixed by
        # reading the alias-collapsed id set the superseded-arm buffer
        # already used.
        M = self._model
        MODELS = list(self.BASE) + [M("claude-opus-5-20260401", "Claude Opus 5",
                                      "2026-04-01T00:00:00Z")]
        PREV = dict(self.PREV0, arms=[{"id": "claude-sonnet-5"},
                                      {"id": "claude-opus-5-20260401"}])

        def usage(n):
            return {"claude-sonnet-5": 1000, "claude-haiku-4-5": 50,
                    "claude-fable-5-1": 0, "claude-opus-5": 55,
                    "claude-opus-5-5": 0}

        def clean(k):
            return self._docs(k, opus="claude-opus-5", sonnet="claude-sonnet-5")

        out, _ = self._loop(usage, 1, clean, previous=PREV, models=MODELS)
        result = out[0]["result"]
        self.assertIn("claude-opus-5", self._arms(result))

    def test_g4b_the_same_seat_retires_correctly_at_half_a_percent(self):
        # g4b.py: R7-2's fix must not paper over a genuine retirement — the
        # same dated-only previous arm, now at 0.5% (under the 2% exit bar),
        # still retires. The negative control: on f7e0ca8 the bug excluded
        # it too, but for the WRONG reason ("the tier is not on the
        # roster" unconditionally, never reaching a real exit check) —
        # this assertion alone was already green there, which is why it is
        # test_g4, not this one, that pins the bug.
        M = self._model
        MODELS = list(self.BASE) + [M("claude-opus-5-20260401", "Claude Opus 5",
                                      "2026-04-01T00:00:00Z")]
        PREV = dict(self.PREV0, arms=[{"id": "claude-sonnet-5"},
                                      {"id": "claude-opus-5-20260401"}])

        def usage(n):
            return {"claude-sonnet-5": 1000, "claude-haiku-4-5": 50,
                    "claude-fable-5-1": 0, "claude-opus-5": 5,
                    "claude-opus-5-5": 0}

        def clean(k):
            return self._docs(k, opus="claude-opus-5", sonnet="claude-sonnet-5")

        out, _ = self._loop(usage, 1, clean, previous=PREV, models=MODELS)
        result = out[0]["result"]
        self.assertNotIn("claude-opus-5", self._arms(result))

    def test_g5_a_mismatch_holds_both_a_dated_and_a_directly_listed_arm(self):
        # g5.py: two previous arms of the same family — one held only under
        # its dated id (`claude-opus-5-20260401`, collapsing onto
        # `claude-opus-5`), one listed directly (`claude-opus-5-5`) — both
        # under one mismatch week. On f7e0ca8 both stayed seated too (the
        # effective default's candidate set is every listed arm, held_here
        # non-empty), but through two DIFFERENT, effective-default-shaped
        # reasons ("seat decided on `claude-opus-5-5`, the newest of the
        # family's listed seats and usage-qualified models" for one, "held
        # over from the previous roster: superseded by ... none retired on
        # a catalogue mismatch" for the other) rather than the one freeze
        # both now get.
        M = self._model
        MODELS = [m for m in self.BASE if m["id"] != "claude-opus-5-5"] + [
            M("claude-opus-5-5", "Claude Opus 5.5", "2026-06-01T00:00:00Z"),
            M("claude-opus-5-20260401", "Claude Opus 5", "2026-04-01T00:00:00Z")]
        PREV = dict(self.PREV0, arms=[{"id": "claude-sonnet-5"},
                                      {"id": "claude-opus-5-20260401"},
                                      {"id": "claude-opus-5-5"}])

        def usage(n):
            return {"claude-sonnet-5": 1000, "claude-haiku-4-5": 50,
                    "claude-opus-5": 5, "claude-opus-5-5": 300}

        def mismatch(k):
            d = self._docs(k)
            d["defaults"]["opus"] = "claude-opus-6"
            return d

        out, _ = self._loop(usage, 1, mismatch, previous=PREV, models=MODELS)
        result = out[0]["result"]
        self.assertIn("claude-opus-5", self._arms(result))
        self.assertIn("claude-opus-5-5", self._arms(result))
        for model_id in ("claude-opus-5", "claude-opus-5-5"):
            self.assertIn("held; none retired on a catalogue mismatch",
                          self._reason(result, model_id))


class TestR9RenamedArmFormSurvivesAFrozenFamily(_WeeklyLoop):
    """R9-1 (#203 probe round 9, adversarial round 9): `frozen_held_ids`
    (built from `previous_arms`/`snapshots` alone) recognized a previous arm
    under its DATED id only when the catalogue listed BOTH the dated id and
    its undated alias this run (the ordinary same-run collapse). If the
    Models API instead switches which SPELLING it lists between runs — the
    dated form gone, only the undated alias remains, or the mirror, the
    undated form gone with only a dated snapshot remaining — a clean run
    still recognizes the renamed arm (`_resolve_defaults`'s
    `_dated_candidates`/undated-collapse fallback), but a run whose probe
    FAILED or MISMATCHED that same week did not: it froze the family, found
    no literal match for the previous arm's old spelling in
    `frozen_held_ids`, and either retired it outright or, worse, let a
    `holds_listed_seat` check pass on an unrelated arm of the same family
    while silently dropping this one's seat. Fixed by `_seated_form`, the
    one helper both `frozen_held_ids` and `seated_in_tier` now use to map a
    previous arm onto whichever spelling THIS run's catalogue lists.

    Each direction is checked against a probe FAILURE and a catalogue
    MISMATCH — the two ways `_resolve_defaults` freezes a family — and each
    asserts the frozen week's arms and its `retired_since_last` are
    IDENTICAL to the same week's clean run: a bad probe must retire nothing
    a clean run keeps."""

    def test_r9a_a_dated_previous_arm_survives_when_only_the_alias_is_listed(self):
        # adv203-probe-r9's repro_rename.py, direction (a): the previous
        # roster names the opus seat under its DATED id
        # `claude-opus-5-5-20260926`; this run's catalogue (`BASE`) lists
        # only the undated alias `claude-opus-5-5`. A clean run resolves
        # the vendor default straight to the alias and retires the dated
        # id as a collapse, not a loss. Before the fix, a frozen week found
        # `claude-opus-5-5-20260926` in neither `previous_arms` (literal)
        # nor `snapshots` (no same-run collapse: the dated form isn't even
        # listed) and excluded the alias outright, even though the OTHER
        # previous arm `claude-opus-5` kept `holds_listed_seat` true — so
        # the alias's seat was silently dropped while the family read as
        # "held".
        PREV = dict(self.PREV0, arms=[{"id": "claude-sonnet-5"},
                                      {"id": "claude-opus-5"},
                                      {"id": "claude-opus-5-5-20260926"}])

        def usage(n):
            return {"claude-sonnet-5": 900, "claude-opus-5": 100,
                    "claude-opus-5-5": 200, "claude-haiku-4-5": 0,
                    "claude-fable-5-1": 0}

        def clean(k):
            return self._docs(k, opus="claude-opus-5-5", sonnet="claude-sonnet-5")

        def probe_failed(k):
            d = self._docs(k, sonnet="claude-sonnet-5")
            d["errors"] = {"opus": "timeout"}
            return d

        def mismatch(k):
            return self._docs(k, opus="claude-opus-9", sonnet="claude-sonnet-5")

        base, _ = self._loop(usage, 1, clean, previous=PREV)
        clean_arms = self._arms(base[0]["result"])
        clean_retired = sorted(r["id"] for r in base[0]["result"]["retired_since_last"])
        self.assertIn("claude-opus-5-5", clean_arms)
        for bad, label in ((probe_failed, "probe failure"), (mismatch, "mismatch")):
            with self.subTest(bad=label):
                out, _ = self._loop(usage, 1, bad, previous=PREV)
                result = out[0]["result"]
                self.assertEqual(self._arms(result), clean_arms)
                self.assertEqual(
                    sorted(r["id"] for r in result["retired_since_last"]),
                    clean_retired)
                self.assertIn("claude-opus-5-5", self._arms(result))
                self.assertIn("held; none retired on",
                              self._reason(result, "claude-opus-5-5"))

    def test_r9b_an_undated_previous_arm_survives_when_only_a_dated_id_is_listed(self):
        # adv203-probe-r9's repro_b.py, direction (b): the previous roster
        # names the opus seat under its UNDATED alias `claude-opus-5`; this
        # run's catalogue lists only a dated snapshot of it,
        # `claude-opus-5-20260401` (the mirror of R9-1(a)). A clean run
        # resolves the vendor default to the sole dated candidate
        # (`_dated_candidates`) and retires the undated previous arm as a
        # collapse onto it. Before the fix, a frozen week found
        # `claude-opus-5` unlisted and its dated form nowhere in
        # `frozen_held_ids`, so `holds_listed_seat("opus")` read false (no
        # OTHER previous opus arm was listed either) and the family fell
        # through to seating a seat by usage or the newest-per-tier
        # fallback instead of holding the same id the clean run seats.
        M = self._model
        MODELS = [m for m in self.BASE if m["id"] != "claude-opus-5"] + [
            M("claude-opus-5-20260401", "Claude Opus 5", "2026-04-01T00:00:00Z")]
        PREV = dict(self.PREV0, arms=[{"id": "claude-sonnet-5"},
                                      {"id": "claude-opus-5"}])

        def usage(n):
            return {"claude-sonnet-5": 900, "claude-opus-5": 55,
                    "claude-opus-5-5": 0, "claude-haiku-4-5": 0,
                    "claude-fable-5-1": 0}

        def clean(k):
            return self._docs(k, opus="claude-opus-5", sonnet="claude-sonnet-5")

        def probe_failed(k):
            d = self._docs(k, sonnet="claude-sonnet-5")
            d["errors"] = {"opus": "timeout"}
            return d

        def mismatch(k):
            return self._docs(k, opus="claude-opus-9", sonnet="claude-sonnet-5")

        base, _ = self._loop(usage, 1, clean, previous=PREV, models=MODELS)
        clean_arms = self._arms(base[0]["result"])
        clean_retired = sorted(r["id"] for r in base[0]["result"]["retired_since_last"])
        self.assertIn("claude-opus-5-20260401", clean_arms)
        for bad, label in ((probe_failed, "probe failure"), (mismatch, "mismatch")):
            with self.subTest(bad=label):
                out, _ = self._loop(usage, 1, bad, previous=PREV, models=MODELS)
                result = out[0]["result"]
                self.assertEqual(self._arms(result), clean_arms)
                self.assertEqual(
                    sorted(r["id"] for r in result["retired_since_last"]),
                    clean_retired)
                self.assertIn("claude-opus-5-20260401", self._arms(result))
                self.assertIn("held; none retired on",
                              self._reason(result, "claude-opus-5-20260401"))


class TestR10RenamedSeatCarriesItsSupersededReason(_RosterFixture):
    """S2 (adversarial round 10): a previous arm listed under a spelling
    this run's catalogue no longer carries (`_seated_form` maps it to the
    id that DOES hold the seat) used to read "no longer returned by the
    Models API" whenever that seated form had itself just retired this
    run (e.g. superseded, `superseded_exit_weeks: 0`) — losing the real
    reason, which lived in `retire_notes` keyed by the seated form, not by
    the previous roster's old spelling. Fixed: when the seated form is not
    an arm this run but IS in `retire_notes`, its reason is reused and
    copied onto the previous roster's own id too."""

    def test_a_renamed_dated_previous_arm_reads_the_same_reason_as_the_control(self):
        # The previous roster lists the opus seat under a dated id this
        # run's catalogue no longer lists at all (`claude-opus-5` — the
        # undated alias — is what THIS run's catalogue has); a clean probe
        # supersedes it with `claude-opus-5-5`, and `superseded_exit_weeks`
        # is 0, so the seated form retires at once. The control keeps the
        # previous arm listed under the literal id this run's catalogue
        # still lists; both must read the identical "superseded by" reason.
        policy = self._policy(superseded_exit_weeks=0)
        renamed_previous = {**self.PREVIOUS, "arms": [
            {"id": "claude-sonnet-5"}, {"id": "claude-opus-5-20260401"}]}
        renamed, _ = self._compute(defaults=self.DEFAULTS, previous=renamed_previous,
                                   policy=policy)
        control, _ = self._compute(defaults=self.DEFAULTS, previous=self.PREVIOUS,
                                   policy=policy)
        control_reason = self._reason(control, "claude-opus-5", "retired_since_last")
        self.assertIn("superseded by `claude-opus-5-5`", control_reason)
        renamed_reason = self._reason(renamed, "claude-opus-5-20260401",
                                      "retired_since_last")
        self.assertEqual(renamed_reason, control_reason)


if __name__ == "__main__":
    unittest.main()
