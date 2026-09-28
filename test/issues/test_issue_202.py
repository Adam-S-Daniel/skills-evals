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
    SOURCE = "claude-code-cli 2.1.283 (Claude Code)"

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
    """Every way a default can fail to resolve FREEZES that family for the
    run (#203 probe round 1): its previous arms are held, nothing of it is
    newly seated — the cooling-off exclusion included — and a warning says
    so. (The class name is historical: it used to fall back to the usage
    rules, and a one-week probe failure then flipped seats.)"""

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

    def test_an_id_that_is_not_available(self):
        defaults = {**self.DEFAULTS, "defaults": {"opus": "claude-opus-9",
                                                  "sonnet": "claude-sonnet-5"}}
        result, warnings = self._compute(defaults=defaults)
        self._assert_todays_opus_rule(result)
        self.assertTrue(any("`opus`" in w and "not an available model" in w
                            for w in warnings), warnings)
        self.assertEqual(result["defaults"]["unresolved"][0]["alias"], "opus")
        self.assertIn("claude-opus-9", result["defaults"]["unresolved"][0]["reason"])

    def test_an_id_in_the_wrong_tier(self):
        defaults = {**self.DEFAULTS, "defaults": {"opus": "claude-sonnet-5"}}
        result, warnings = self._compute(defaults=defaults)
        self._assert_todays_opus_rule(result)
        self.assertTrue(any("`opus`" in w and "sonnet tier" in w for w in warnings),
                        warnings)

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
    """No probe document at all is the pre-#202 roster, byte for byte. A
    document that failed entirely is NOT (#203 probe round 1): it freezes
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
        self.assertIn("no seat changes", said[0])
        self.assertNotIn("usage and newest-in-tier rules", said[0])


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
                self.assertIn("no seat changes", lines[0])
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

    HELD = ("vendor default for `opus` unknown this run (probe: timeout); held, "
            "no seat changes on a failed probe")

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
        # Recorded as an error instead, mythos is frozen like the rest.
        out, _ = self._loop(usage, 1, self._failing(
            {0}, {**errors, "mythos": "no-init"}), models=models)
        self.assertNotIn("claude-mythos-1", self._arms(out[0]["result"]))
        self.assertIn("mythos", out[0]["result"]["defaults_failed"])

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

    def test_any_unresolved_alias_freezes_its_family(self):
        # An id the catalogue does not list, or one of another family: the
        # default is still unknown this run, so the family is frozen, with a
        # class naming why.
        for defaults, cls in (({"opus": "claude-opus-9"}, "not-available"),
                              ({"opus": "claude-sonnet-5"}, "wrong-tier")):
            with self.subTest(cls=cls):
                doc = {**self.DEFAULTS, "defaults": {**defaults,
                                                     "sonnet": "claude-sonnet-5"}}
                result, _ = self._compute(defaults=doc)
                self.assertEqual(result["defaults_failed"], {"opus": cls})
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


class TestProposeStepOnAFailedProbe(unittest.TestCase):
    """F3 (#203 probe round 1): eval.yml's "Propose a roster change" step
    warns with a fixed text when the computed roster carries
    `defaults_failed`, and keeps the tracking issue open even on "same"."""

    START = "# >>> defaults-failed note"
    END = "# <<< defaults-failed note"
    WARNING = "::warning::vendor-default probe failed for {n} families; their seats were held"
    MARKER = "<!-- skills-evals:roster-proposal -->"

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

    @unittest.skipUnless(shutil.which("bash"), "needs bash")
    def test_a_failed_probe_warns_with_the_fixed_text(self):
        out = self._run_fragment({"proposal": {"status": "same"},
                                  "defaults_failed": {"opus": "timeout",
                                                      "sonnet": "no-init"}})
        self.assertIn(self.WARNING.format(n=2) + "\n", out)
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

    def test_the_fragment_interpolates_nothing(self):
        fragment = self._fragment()
        self.assertNotIn("${{", fragment)
        # The warning's text is fixed: the only expansion in it is the count
        # the fragment itself validated as digits.
        line = next(ln for ln in fragment.splitlines() if "::warning::" in ln)
        self.assertEqual(re.findall(r"\$\{?(\w+)", line), ["defaults_failed"])

    def _run_step(self, latest, issues):
        """The whole step body with a stub `gh`, from the tracker listing to
        the "same" branch — which is as far as a "same" run goes."""
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
                              text=True, timeout=60, env=env, cwd=self.tmp)
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

    @unittest.skipUnless(shutil.which("bash") and shutil.which("jq"), "needs bash and jq")
    def test_same_with_a_failed_probe_opens_the_issue(self):
        out, calls, body = self._run_step(self.FAILED, [])
        self.assertIn(self.WARNING.format(n=1), out)
        self.assertEqual(len(calls), 1, calls)
        self.assertTrue(calls[0].startswith("issue create"), calls)
        self.assertIn("probe failed", calls[0])
        self.assertTrue(body.startswith(self.MARKER), body)
        self.assertIn("The vendor-default probe failed for 1 families", body)
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


class TestWorkflowProbeFallbackDocument(unittest.TestCase):
    """A probe that exits non-zero writes no document; the roster step then
    writes an empty one in its place, so the roster freezes every family
    rather than reading "no probe at all" (F1 + F7, #203 probe round 1)."""

    def test_a_failed_probe_leaves_a_document_that_freezes(self):
        doc = yaml.safe_load(EVAL_WORKFLOW.read_text(encoding="utf-8"))
        script = next(s for s in doc["jobs"]["eval"]["steps"]
                      if "roster" in (s.get("name") or "").lower())["run"]
        line = next(ln.strip() for ln in script.splitlines()
                    if "scripts/probe_model_defaults.py" in ln
                    and not ln.strip().startswith("#"))
        self.assertIn("|| printf '{}\\n' > \"$work/defaults.json\"", line)
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
    of those freeze the family (F1)."""

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
        self.assertEqual(result["defaults_failed"], {"opus": "not-available"})
        self.assertIn("not an available model",
                      result["defaults"]["unresolved"][0]["reason"])

    def test_two_dated_candidates_are_ambiguous_and_freeze(self):
        result, warnings = self._compute(defaults=self.DEFAULTS, models=self._catalogue(
            "claude-opus-5-5-20260926", "claude-opus-5-5-20261001"))
        self.assertEqual(result["defaults_failed"], {"opus": "ambiguous-snapshot"})
        self.assertNotIn("opus", result["defaults"]["resolved"])
        why = result["defaults"]["unresolved"][0]["reason"]
        self.assertIn("2 dated snapshots", why)
        self.assertEqual(sorted(self._arms(result)), ["claude-opus-5", "claude-sonnet-5"])

    def test_a_dated_id_of_another_base_is_not_a_candidate(self):
        # `claude-opus-5-20260101` is a snapshot of opus-5, not of opus-5-5.
        result, _ = self._compute(defaults=self.DEFAULTS, models=self._catalogue(
            "claude-opus-5-20260101"))
        self.assertEqual(result["defaults_failed"], {"opus": "not-available"})


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


if __name__ == "__main__":
    unittest.main()
