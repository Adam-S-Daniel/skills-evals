"""harness/cache_ttl.py: the prompt-cache TTL policy (owner's rule, 2026-11-20:
use the 1-hour cache where it is cheaper or nominally the same cost; API-billed
lanes keep 5m because dollars decide). Invented weights except the one
integration test against the locked table. No network, no wall clock."""

from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "harness"))
sys.path.insert(0, str(ROOT / "scripts"))
import allowance_points  # noqa: E402
import cache_ttl  # noqa: E402
import guidance  # noqa: E402
import loop_status  # noqa: E402

TTL = "CLAUDE_CODE_PROMPT_CACHE_TTL"
SUB = "CLAUDE_CODE_SUBAGENT_PROMPT_CACHE_TTL"


def row(w5, w1):
    return {"cache_write_5m": {"point": w5, "basis": "measured"},
            "cache_write_1h": {"point": w1, "basis": "assumed"}}


def doc(**meters):
    return {"id": "t", "meters": {m: {"models": models} for m, models in meters.items()}}


class VerdictTests(unittest.TestCase):
    def test_cheaper_and_equal_are_1h(self):
        v = cache_ttl.model_verdicts(doc(all_models={"a": row(1.0, 0.8), "b": row(2.0, 2.0)}))
        self.assertEqual({m: x["ttl"] for m, x in v.items()}, {"a": "1h", "b": "1h"})
        self.assertEqual(v["a"]["w5m"], 1.0)
        self.assertEqual(v["a"]["basis_1h"], "assumed")

    def test_tolerance_edge(self):
        at = cache_ttl.model_verdicts(doc(all_models={"a": row(100.0, 100.0 * 1.03)}))
        over = cache_ttl.model_verdicts(doc(all_models={"a": row(100.0, 100.0 * 1.0301)}))
        self.assertEqual(at["a"]["ttl"], "1h")
        self.assertEqual(over["a"]["ttl"], "5m")

    def test_one_5m_meter_makes_the_model_5m(self):
        v = cache_ttl.model_verdicts(doc(all_models={"a": row(1.0, 0.5)},
                                         fable={"a": row(1.0, 1.5)}))
        self.assertEqual(v["a"]["ttl"], "5m")
        self.assertEqual([m["ttl"] for m in v["a"]["meters"]], ["1h", "5m"])

    def test_one_5m_model_flips_the_subscription_verdict(self):
        good = doc(all_models={"a": row(1.0, 0.9), "b": row(1.0, 1.0)})
        bad = doc(all_models={"a": row(1.0, 0.9), "b": row(1.0, 1.5)})
        self.assertEqual(cache_ttl.subscription_ttl(good), ("1h", []))
        ttl, reasons = cache_ttl.subscription_ttl(bad)
        self.assertEqual(ttl, "5m")
        self.assertEqual(len(reasons), 1)

    def test_missing_rows_are_5m_with_a_reason(self):
        v = cache_ttl.model_verdicts(doc(all_models={"a": {"cache_write_5m": {"point": 1.0}}}))
        self.assertEqual(v["a"]["ttl"], "5m")
        self.assertTrue(v["a"]["reasons"])
        self.assertEqual(cache_ttl.subscription_ttl({})[0], "5m")
        self.assertEqual(cache_ttl.subscription_ttl(None)[0], "5m")

    def test_the_locked_table_says_1h_today(self):
        weights = allowance_points.table()
        self.assertEqual(cache_ttl.subscription_ttl(weights)[0], "1h")
        v = cache_ttl.model_verdicts(weights)
        self.assertEqual(v["claude-fable-5-2"]["ttl"], "1h")
        self.assertLess(v["claude-fable-5-2"]["w1h"], v["claude-fable-5-2"]["w5m"])


class LaneTests(unittest.TestCase):
    def test_lane_detection(self):
        self.assertFalse(cache_ttl.lane_bills_api({"PATH": "/bin", "ANTHROPIC_API_KEY": ""}))
        for name in cache_ttl.API_LANE_ENV:
            with self.subTest(name=name):
                self.assertTrue(cache_ttl.lane_bills_api({name: "x"}))

    def test_ttl_env_subscription(self):
        out = cache_ttl.ttl_env({"PATH": "/bin", TTL: "5m", "FORCE_PROMPT_CACHING_5M": "1"},
                                doc(all_models={"a": row(1.0, 1.0)}))
        self.assertEqual(out, {"PATH": "/bin", TTL: "1h", SUB: "1h"})

    def test_ttl_env_subscription_falls_to_5m(self):
        out = cache_ttl.ttl_env({}, doc(all_models={"a": row(1.0, 2.0)}))
        self.assertEqual(out, {TTL: "5m", SUB: "5m"})

    def test_ttl_env_api_lane(self):
        env = {"ANTHROPIC_AUTH_TOKEN": "t", TTL: "1h", SUB: "1h", "ENABLE_PROMPT_CACHING_1H": "1"}
        out = cache_ttl.ttl_env(env, doc(all_models={"a": row(1.0, 0.5)}))
        self.assertEqual(out, {"ANTHROPIC_AUTH_TOKEN": "t", "FORCE_PROMPT_CACHING_5M": "1"})
        self.assertIn(TTL, env)  # input not mutated


class ChildEnvTests(unittest.TestCase):
    def test_ambient_5m_is_overridden_on_a_subscription(self):
        env = guidance.cli_child_env({"PATH": "/bin", TTL: "5m"})
        self.assertEqual(env[TTL], "1h")
        self.assertEqual(env[SUB], "1h")
        self.assertEqual(env["CLAUDE_CODE_DISABLE_AUTO_MEMORY"], "1")
        self.assertNotIn("FORCE_PROMPT_CACHING_5M", env)

    def test_api_lane_is_forced_to_5m(self):
        env = guidance.cli_child_env({"ANTHROPIC_AUTH_TOKEN": "t", TTL: "1h"})
        self.assertEqual(env["FORCE_PROMPT_CACHING_5M"], "1")
        self.assertNotIn(TTL, env)

    def test_unreadable_table_falls_back_to_5m(self):
        with mock.patch.object(cache_ttl, "locked_weights",
                               side_effect=allowance_points.LockError("x")):
            env = guidance.cli_child_env({})
        self.assertEqual((env[TTL], env[SUB]), ("5m", "5m"))


class ApplySettingsTests(unittest.TestCase):
    def setUp(self):
        self.dir = Path(tempfile.mkdtemp())
        self.addCleanup(lambda: __import__("shutil").rmtree(self.dir, ignore_errors=True))
        self.path = self.dir / "settings.json"

    def test_creates_the_key_and_keeps_the_rest(self):
        self.path.write_text(json.dumps({"model": "x", "promptCacheTtl": "5m"}), encoding="utf-8")
        self.assertEqual(cache_ttl.apply_settings(self.path, "1h"), "applied")
        self.assertEqual(json.loads(self.path.read_text()),
                         {"model": "x", "promptCacheTtl": "5m", "subagentPromptCacheTtl": "1h"})
        self.assertTrue(self.path.read_text().endswith("}\n"))
        self.assertEqual(os.listdir(self.dir), ["settings.json"])

    def test_noop_when_equal(self):
        self.path.write_text('{"subagentPromptCacheTtl":"1h"}', encoding="utf-8")
        self.assertEqual(cache_ttl.apply_settings(self.path, "1h"), "unchanged")
        self.assertEqual(self.path.read_text(), '{"subagentPromptCacheTtl":"1h"}')

    def test_dry_run_writes_nothing(self):
        self.path.write_text("{}", encoding="utf-8")
        self.assertEqual(cache_ttl.apply_settings(self.path, "1h", dry_run=True), "applied")
        self.assertEqual(self.path.read_text(), "{}")

    def test_refuses_invalid_input_with_exit_2_and_a_fixed_message(self):
        for text in ("{not json SECRET", "[1]"):
            with self.subTest(text=text):
                self.path.write_text(text, encoding="utf-8")
                with mock.patch("sys.stderr") as err, \
                        mock.patch.object(cache_ttl, "locked_weights",
                                          return_value=doc(all_models={"a": row(1, 1)})):
                    code = cache_ttl.main(["apply-settings", "--settings", str(self.path)])
                self.assertEqual(code, 2)
                printed = "".join(c.args[0] for c in err.write.call_args_list)
                self.assertIn(cache_ttl.INVALID_SETTINGS, printed)
                self.assertNotIn("SECRET", printed)
                self.assertEqual(self.path.read_text(), text)

    def test_replace_is_atomic(self):
        self.path.write_text("{}", encoding="utf-8")
        with mock.patch("os.replace", side_effect=OSError("boom")):
            with self.assertRaises(OSError):
                cache_ttl.apply_settings(self.path, "1h")
        self.assertEqual(self.path.read_text(), "{}")
        self.assertEqual(os.listdir(self.dir), ["settings.json"])


def entry(w5, w1, model="m", side=False):
    return json.dumps({"isSidechain": side, "message": {
        "model": model, "usage": {"cache_creation": {
            "ephemeral_5m_input_tokens": w5, "ephemeral_1h_input_tokens": w1}}}})


class VerifyTests(unittest.TestCase):
    def setUp(self):
        self.dir = Path(tempfile.mkdtemp())
        self.addCleanup(lambda: __import__("shutil").rmtree(self.dir, ignore_errors=True))
        self.weights = doc(all_models={"m": row(1.0, 1.0)})

    def write(self, name, lines, mtime=1_000_000.0):
        path = self.dir / name
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        os.utime(path, (mtime, mtime))

    def test_tally_splits_by_bucket_and_model_and_skips_junk(self):
        self.write("a.jsonl", [entry(0, 10), entry(0, 5, "n"), entry(3, 0, side=True),
                               "not json", json.dumps({"message": {"usage": {}}}),
                               entry(-1, 1), entry(True, 1)])
        t = cache_ttl.tally(self.dir, 24, now=1_000_000.0 + 3600)
        self.assertEqual(t["main"], {"m": {"w5m": 0, "w1h": 10}, "n": {"w5m": 0, "w1h": 5}})
        self.assertEqual(t["subagent"], {"m": {"w5m": 3, "w1h": 0}})

    def test_window_excludes_old_files(self):
        self.write("old.jsonl", [entry(0, 10)], mtime=1_000_000.0)
        t = cache_ttl.tally(self.dir, 1, now=1_000_000.0 + 7200)
        self.assertEqual(t, {"main": {}, "subagent": {}})

    def test_verify_ok_and_mismatch(self):
        self.write("a.jsonl", [entry(0, 10), entry(0, 7, side=True)])
        report = cache_ttl.verify(self.dir, 24, self.weights, now=1_000_000.0 + 60)
        self.assertTrue(report["ok"])
        self.write("b.jsonl", [entry(4, 6, side=True), entry(2, 0)])
        report = cache_ttl.verify(self.dir, 24, self.weights, now=1_000_000.0 + 60)
        self.assertFalse(report["ok"])
        self.assertFalse(report["buckets"]["main"]["ok"])
        self.assertFalse(report["buckets"]["subagent"]["ok"])
        self.assertNotIn(str(self.dir), json.dumps(report))

    def test_verify_cli_exits_0_on_mismatch(self):
        self.write("a.jsonl", [entry(9, 0)])
        with mock.patch.object(cache_ttl, "locked_weights", return_value=self.weights), \
                mock.patch("time.time", return_value=1_000_060.0), \
                mock.patch("builtins.print") as out:
            code = cache_ttl.main(["verify", "--projects", str(self.dir)])
        self.assertEqual(code, 0)
        self.assertFalse(json.loads(out.call_args.args[0])["ok"])


class LoopStatusSectionTests(unittest.TestCase):
    def test_section_with_no_paths_is_skipped(self):
        block = loop_status.cache_ttl_block()
        self.assertEqual(block["subscription_ttl"], "1h")
        self.assertEqual(block["settings"], "skipped")
        self.assertIsNone(block["verify"])
        self.assertEqual(set(block["per_model"].values()), {"1h"})
        self.assertEqual(block["table"], allowance_points.table()["id"])

    def test_settings_applied_unchanged_error_and_verify(self):
        with tempfile.TemporaryDirectory() as d:
            settings, projects = Path(d) / "s.json", Path(d) / "p"
            projects.mkdir()
            settings.write_text("{}", encoding="utf-8")
            self.assertEqual(loop_status.cache_ttl_block(settings)["settings"], "applied")
            self.assertEqual(loop_status.cache_ttl_block(settings)["settings"], "unchanged")
            block = loop_status.cache_ttl_block(settings, projects)
            self.assertTrue(block["verify"]["ok"])
            settings.write_text("nope", encoding="utf-8")
            self.assertEqual(loop_status.cache_ttl_block(settings)["settings"], "error")

    def test_unreadable_table_is_a_fixed_error(self):
        with mock.patch.object(cache_ttl, "locked_weights",
                               side_effect=allowance_points.LockError("/secret/path")):
            block = loop_status.cache_ttl_block()
        self.assertEqual(block["settings"], "error")
        self.assertNotIn("secret", json.dumps(block))


if __name__ == "__main__":
    unittest.main()
