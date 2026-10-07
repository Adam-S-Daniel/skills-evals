"""The board snapshot reads git objects as data and writes only its output.

Example repositories are local, deterministic, and have no push remotes.
Run through the repository's process-safe test wrapper in a PID namespace.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
import board_feed as feed

STAMP = "20261001T120000Z"
LATER = "20261002T120000Z"


def single(**changes):
    doc = {"objective_checks": [{"passed": True}, {"passed": False}],
           "agent": {"usage": {"input_tokens": 10, "output_tokens": 5,
                    "cache_creation_input_tokens": 3, "cache_read_input_tokens": 2},
                    "cost_usd": 0.25, "num_turns": 4},
           "judge": {"overall": 8}, "models_used": ["example-model"], "n": 1}
    doc.update(changes)
    return doc


def aggregate():
    return {"n": 3, "models_used": ["example-model"], "aggregate": {
        "objective": {"mean_passed": 1.5, "mean_total": 2},
        "judge": {"overall": {"mean": 7.5}}, "cost_usd": {"mean": 0.4},
        "efficiency": {"input_tokens": {"mean": 11}, "output_tokens": {"mean": 6},
            "cache_creation_input_tokens": {"mean": 4},
            "cache_read_input_tokens": {"mean": 3}, "num_turns": {"mean": 5}}}}


class BoardFeedTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.repo = Path(self.temp.name) / "repo"
        self.repo.mkdir()
        self.out = Path(self.temp.name) / "board.json"
        self.git("init", "-q", "--initial-branch=main")
        self.git("config", "user.name", "Example")
        self.git("config", "user.email", "example@example.com")
        self.write("evals/workflow-path-audit/fixture.yaml", "skill: workflow-path-audit\n")
        self.main = self.commit("Fixture inventory")
        self.git("branch", "results-ref")
        self.git("checkout", "-q", "results-ref")

    def git(self, *args):
        env = {**os.environ, "GIT_CONFIG_NOSYSTEM": "1",
               "GIT_AUTHOR_DATE": "2026-10-03T12:00:00+00:00",
               "GIT_COMMITTER_DATE": "2026-10-03T12:00:00+00:00"}
        return subprocess.run(["git", "-c", "maintenance.auto=false", "-c", "gc.auto=0",
            "-C", str(self.repo), *args], env=env,
            capture_output=True, check=True).stdout.decode().strip()

    def write(self, path, value):
        target = self.repo / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(value) if isinstance(value, (dict, list)) else value,
                          encoding="utf-8")

    def commit(self, message="Example result"):
        self.git("add", ".")
        self.git("commit", "-q", "-m", message)
        return self.git("rev-parse", "HEAD")

    def summary(self, prefix="results", key="workflow-path-audit", stamp=STAMP,
                arm="with_skill", doc=None):
        subject, _, fixture = key.partition("/")
        path = f"{prefix}/{subject}/{stamp}/" + (fixture + "/" if fixture else "") + f"{arm}/summary.json"
        self.write(path, single() if doc is None else doc)
        return path

    def build(self):
        return feed.build_feed(self.repo, self.main, "results-ref")["dash"]

    def test_single_metrics_and_report_are_derived_without_model_pins(self):
        self.summary()
        report = f"results/workflow-path-audit/{STAMP}/report.md"
        self.write(report, "# Example report\n<script>never execute</script>\n")
        sha = self.commit()
        dash = self.build()
        row = dash["results"]["rows"][0]
        self.assertEqual(row["fixture"], "workflow-path-audit")
        self.assertEqual(row["model"], "example-model")
        self.assertEqual(row["report"], "# Example report\n<script>never execute</script>\n")
        self.assertEqual(row["url"], f"{feed.REPOSITORY}/blob/{sha}/{report}")
        self.assertEqual(row["arms"], [{"arm": "with_skill", "obj": 1, "total": 2,
                         "judge": 8, "tokens": 20, "turns": 4, "cost": 0.25, "n": 1}])
        self.assertIsNone(row["note"])
        self.assertEqual(dash["trend"]["points"][0]["without_skill"], None)

    def test_aggregate_means_suppress_trial_children(self):
        self.summary(doc=aggregate())
        self.summary(arm="with_skill/trial-1", doc=single(agent={"num_turns": 999}))
        self.commit()
        arm = self.build()["results"]["rows"][0]["arms"][0]
        self.assertEqual(arm, {"arm": "with_skill", "obj": 1.5, "total": 2,
            "judge": 7.5, "tokens": 24, "turns": 5, "cost": 0.4, "n": 3})

    def test_trial_only_results_mean_metrics_and_count_trials(self):
        self.summary(arm="with_skill/trial-1")
        self.summary(arm="with_skill/trial-2", doc=single(judge={"overall": 6}))
        self.summary(key="overflow", arm="with_skill/trial-1", doc=single(agent={"cost_usd": 1e308}))
        self.summary(key="overflow", arm="with_skill/trial-2", doc=single(agent={"cost_usd": 1e308}))
        self.commit()
        rows = {row["fixture"]: row for row in self.build()["results"]["rows"]}
        arm = rows["workflow-path-audit"]["arms"][0]
        self.assertEqual(arm["n"], 2)
        self.assertEqual(arm["judge"], 7)
        self.assertEqual(arm["tokens"], 20)
        self.assertIsNone(rows["overflow"]["arms"][0]["cost"])

    def test_all_roots_newest_selection_and_stable_run_tiebreak(self):
        prefixes = ("results", "eval-results", "eval-results/20261001T130000Z-abcdef",
                    "routine-results/20261002T130000Z-abcdef", "results/20261002T140000Z-abcdef")
        for index, prefix in enumerate(prefixes):
            self.summary(prefix=prefix, stamp=STAMP if index < 3 else LATER,
                         doc=single(judge={"overall": index}))
        self.summary(key="other-skill/nested-fixture")
        self.commit()
        rows = {row["fixture"]: row for row in self.build()["results"]["rows"]}
        row = rows["workflow-path-audit"]
        self.assertEqual(row["runs"], 5)
        self.assertEqual(row["ts"], LATER)
        self.assertEqual(row["arms"][0]["judge"], 3)
        self.assertEqual(rows["other-skill/nested-fixture"]["runs"], 1)

    def test_trend_preserves_source_runs_without_cross_run_arm_pairing(self):
        self.summary(stamp=LATER, arm="without_skill")
        self.summary(prefix="routine-results/20261001T140000Z-abcdef")
        self.summary(arm="without_skill")
        self.summary(key="workflow-path-audit/nested-fixture")
        self.commit()
        points = self.build()["trend"]["points"]
        self.assertEqual(len(points), 3)
        self.assertEqual([point["ts"] for point in points], [STAMP, STAMP, LATER])
        self.assertIsNone(points[0]["with_skill"])
        self.assertIsNone(points[1]["without_skill"])
        self.assertIsNone(points[2]["with_skill"])
        self.assertEqual(set(points[1]["with_skill"]), set(feed.METRICS))
        self.assertIn("workflow-path-audit/nested-fixture",
                      [row["fixture"] for row in self.build()["results"]["rows"]])

    def test_malformed_summaries_and_reports_remain_unknown(self):
        cases = ("{", '{"agent":{},"agent":{}}', '{"judge":{"overall":NaN}}',
                 '{"judge":{"overall":1e999}}', '[' * 20 + '0' + ']' * 20,
                 "x" * 65537, "\x00")
        for index, raw in enumerate(cases):
            self.summary(key=f"bad-{index}", doc=raw)
        self.write(f"results/report-only/{STAMP}/report.md", "# Report only\n")
        self.write(f"results/bad-0/{STAMP}/report.md", "\x00")
        self.summary(key="bad-0", arm="with_skill/trial-1")
        self.commit()
        rows = {row["fixture"]: row for row in self.build()["results"]["rows"]}
        for index in range(len(cases)):
            row = rows[f"bad-{index}"]
            self.assertTrue(all(value is None for key, value in row["arms"][0].items() if key != "arm"))
            self.assertIsNone(row["url"])
            self.assertIsNone(row["model"])
        self.assertEqual(rows["report-only"]["arms"], [])
        self.assertEqual(rows["report-only"]["report"], "# Report only\n")

    def test_invalid_numeric_fields_and_missing_usage_are_null(self):
        docs = [single(agent={"usage": {"input_tokens": 2}, "num_turns": True,
                            "cost_usd": -1}, judge={"overall": "8"},
                            objective_checks=[{"passed": "yes"}]),
                single(agent={"usage": {"input_tokens": 2, "output_tokens": 3,
                            "cache_read_input_tokens": None}}),
                single(agent={"usage": {"input_tokens": 2, "output_tokens": 3}}),
                single(objective_checks=[], models_used=[], n=None),
                single(agent={"model": "example-fallback"}, models_used=None)]
        for index, doc in enumerate(docs):
            self.summary(key=f"invalid-{index}", doc=doc)
        self.commit()
        rows = {row["fixture"]: row for row in self.build()["results"]["rows"]}
        first = rows["invalid-0"]["arms"][0]
        self.assertTrue(all(first[key] is None for key in feed.METRICS))
        self.assertIsNone(rows["invalid-1"]["arms"][0]["tokens"])
        self.assertEqual(rows["invalid-2"]["arms"][0]["tokens"], 5)
        self.assertEqual(rows["invalid-3"]["arms"][0]["obj"], 0)
        self.assertIsNone(rows["invalid-3"]["model"])
        self.assertIsNone(rows["invalid-3"]["arms"][0]["n"])
        self.assertEqual(rows["invalid-4"]["model"], "example-fallback")

    def test_empty_wrong_shape_and_fractional_counts_are_unknown(self):
        for index, doc in enumerate(({}, {"agent": []}, single(n=1.5), single(n=True),
                                      single(n=0))):
            self.summary(key=f"count-{index}", doc=doc)
        self.summary(key="malformed-trials", arm="with_skill/trial-1", doc={})
        self.summary(key="malformed-trials", arm="with_skill/trial-2", doc={})
        self.summary(key="timed-out", doc={"n": 3, "error": {"type": "TimeoutError"}})
        self.commit()
        for row in self.build()["results"]["rows"]:
            if row["fixture"] == "timed-out":
                self.assertEqual(row["arms"][0]["n"], 3)
                self.assertTrue(all(row["arms"][0][key] is None for key in feed.METRICS))
            else:
                self.assertIsNone(row["arms"][0]["n"])

    def test_aggregate_tokens_require_matching_observation_sets(self):
        for index, (key, value) in enumerate((("n_missing", 1), ("n", 2), ("n", True))):
            doc = aggregate()
            efficiency = doc["aggregate"]["efficiency"]
            for block in efficiency.values():
                block["n"] = 3
                block["n_missing"] = 0
            efficiency["input_tokens"][key] = value
            self.summary(key=f"subset-{index}", doc=doc)
        self.commit()
        for row in self.build()["results"]["rows"]:
            self.assertIsNone(row["arms"][0]["tokens"])

    def test_inventory_counts_main_fixtures_and_queries_excluding_seed_and_references(self):
        self.git("checkout", "-q", "main")
        self.write("evals/workflow-path-audit/nested/fixture.yaml", "skill: workflow-path-audit\n")
        self.write("evals/another-skill/fixture.yaml", "skill: another-skill\n")
        self.write("evals/guidance/section/fixture.yaml", "subject: guidance\nsection: security\n")
        self.write("evals/workflow-path-audit/seed/fixture.yaml", "skill: fake\n")
        self.write("evals/another-skill/references/fixture.yaml", "skill: fake\n")
        query = [{"query": "Does example.com need a path filter?", "should_trigger": True}]
        self.write("evals/workflow-path-audit/trigger-eval-set.json", query)
        self.write("evals/another-skill/trigger-eval-set.json", query * 2)
        self.write("evals/workflow-path-audit/seed/trigger-eval-set.json", query * 3)
        self.main = self.commit("Expanded fixtures")
        self.git("checkout", "-q", "results-ref")
        self.summary()
        self.write("evals/another-skill/fixture.yaml", "skill: fake-results-inventory\n")
        self.commit()
        inventory = self.build()["inventory"]
        self.assertEqual((inventory["total"], inventory["dirs"], inventory["minFixtures"]), (3, 2, 1))
        self.assertEqual(inventory["triggerSet"], 3)
        self.assertEqual(inventory["guidance"]["sections"], 1)
        self.assertIsNone(inventory["guidance"]["gap"])
        skills = {skill["name"]: skill for skill in inventory["skills"]}
        self.assertIsNone(skills["another-skill"]["results"])
        self.assertEqual(skills["workflow-path-audit"]["count"], 2)
        self.assertEqual(skills["workflow-path-audit"]["url"],
                         feed.link("tree", self.main, "evals/workflow-path-audit"))
        self.assertEqual(skills["workflow-path-audit"]["trigger"],
                         feed.link("blob", self.main, "evals/workflow-path-audit/trigger-eval-set.json"))

    def test_malformed_inventory_does_not_claim_zero_coverage(self):
        self.git("checkout", "-q", "main")
        self.write("evals/broken/fixture.yaml", "skill: one\nskill: two\n")
        self.write("evals/broken/trigger-eval-set.json", [{"query": "example.net"}])
        self.main = self.commit()
        inventory = self.build()["inventory"]
        self.assertTrue(all(inventory[key] is None for key in ("total", "dirs", "minFixtures", "triggerSet")))
        self.assertIsNone(inventory["guidance"]["sections"])
        self.assertIsNone(inventory["skills"][0]["trigger"])

    def test_invalid_fixture_fields_and_query_shapes_are_unknown(self):
        self.git("checkout", "-q", "main")
        self.write("evals/broken/fixture.yaml", "skill: null\n")
        self.write("evals/guidance/section/fixture.yaml", "subject: guidance\nsection: []\n")
        self.write("evals/workflow-path-audit/trigger-eval-set.json", {})
        self.write("evals/fixture.yaml", "skill: root-fixture\n")
        self.main = self.commit()
        inventory = self.build()["inventory"]
        self.assertIsNone(inventory["total"])
        self.assertIsNone(inventory["guidance"]["sections"])
        self.assertIsNone(inventory["triggerSet"])
        skills = {skill["name"]: skill for skill in inventory["skills"]}
        self.assertIsNone(skills["workflow-path-audit"]["trigger"])
        self.assertEqual(skills["root-fixture"]["url"], feed.link("tree", self.main, "evals"))
        self.assertIsNone(feed.query_count([{"query": " ", "should_trigger": True}]))

    def test_symlinks_bad_timestamps_and_nonresult_paths_are_ignored(self):
        path = self.repo / f"results/linked/{STAMP}/with_skill/summary.json"
        path.parent.mkdir(parents=True)
        path.symlink_to("../../../../example.json")
        self.write("example.json", single())
        self.summary(key="impossible", stamp="20261301T120000Z")
        self.summary(prefix="outside")
        self.write(f"results/workflow-path-audit/{STAMP}/raw.json", single())
        self.commit()
        self.assertEqual(self.build()["results"]["rows"], [])

    def test_error_note_exposes_type_without_detail_or_untrusted_free_text(self):
        self.summary(doc=single(error={"type": "TimeoutError", "detail": "private example.com detail"},
                                note="untrusted free-form detail"))
        self.summary(arm="without_skill", doc=single(error={"type": "example@example.com"}))
        self.commit()
        self.assertEqual(self.build()["results"]["rows"][0]["note"], "TimeoutError")

    def test_cli_is_deterministic_and_writes_only_output_from_commit_objects(self):
        self.summary()
        result_sha = self.commit()
        self.write(f"results/workflow-path-audit/{STAMP}/with_skill/summary.json", single(judge={"overall": 0}))
        before = {str(path.relative_to(self.repo)): path.read_bytes()
                  for path in self.repo.rglob("*") if path.is_file()}
        args = ["--repo", str(self.repo), "--main-ref", self.main,
                "--results-ref", "results-ref", "--out", str(self.out)]
        self.assertEqual(feed.main(args), 0)
        raw = self.out.read_bytes()
        self.assertEqual(feed.main(args), 0)
        self.assertEqual(raw, self.out.read_bytes())
        after = {str(path.relative_to(self.repo)): path.read_bytes()
                 for path in self.repo.rglob("*") if path.is_file()}
        self.assertEqual(before, after)
        dash = json.loads(raw)["dash"]
        self.assertEqual(dash["results"]["rows"][0]["arms"][0]["judge"], 8)
        self.assertEqual(dash["meta"]["mainSha"], self.main)
        self.assertEqual(dash["meta"]["resultsSha"], result_sha)
        self.assertEqual(dash["meta"]["asOf"], "2026-10-03T12:00:00Z")

    def test_invalid_refs_fail_without_output_or_option_injection(self):
        for ref in ("missing-ref", "--help", "--output=example.net"):
            with self.subTest(ref=ref):
                self.assertEqual(feed.main(["--repo", str(self.repo), "--main-ref=" + ref,
                    "--results-ref", "results-ref", "--out", str(self.out)]), 2)
                self.assertFalse(self.out.exists())

    def test_fresh_cli_import_does_not_create_bytecode_outside_output(self):
        self.summary()
        self.commit()
        code = Path(self.temp.name) / "code"
        code.mkdir()
        for filename in ("board_feed.py", "ingest_routine_results.py"):
            shutil.copyfile(ROOT / "scripts" / filename, code / filename)
        before = sorted(str(path.relative_to(code)) for path in code.rglob("*"))
        env = dict(os.environ)
        env.pop("PYTHONDONTWRITEBYTECODE", None)
        process = subprocess.run([sys.executable, "board_feed.py",
            "--repo", str(self.repo), "--main-ref", self.main, "--results-ref", "results-ref",
            "--out", str(self.out)], cwd=code, env=env, capture_output=True)
        self.assertEqual(process.returncode, 0, process.stderr.decode())
        self.assertEqual(before, sorted(str(path.relative_to(code)) for path in code.rglob("*")))
        self.assertTrue(self.out.exists())


if __name__ == "__main__":
    unittest.main()
