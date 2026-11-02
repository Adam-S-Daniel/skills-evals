"""scripts/harvest_judge_rationales.py: candidate objective checks from the
judge rationales of pairs the objective checks did not separate
(skills-evals#550, form 1)."""
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import harvest_judge_rationales as hjr  # noqa: E402

TS = "20260801T100000Z"


def _write(path: Path, doc) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc), encoding="utf-8")


def _arm(passed, overall=None, dims=None):
    doc = {"objective_checks": [{"id": f"c{i}", "passed": i < passed, "detail": ""}
                                for i in range(3)]}
    if dims is not None:
        doc["judge"] = {"overall": overall, "dimensions": [
            {"name": n, "score": s, "rationale": r} for n, s, r in dims]}
    return doc


class HarvestTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.tree = Path(self._tmp.name) / "tree"
        self.evals = Path(self._tmp.name) / "evals"
        self.tree.mkdir()
        self.evals.mkdir()

    def skill_pair(self, run, key, with_doc, without_doc, fixture=None):
        base = self.tree / "results" / key / run
        if fixture:
            base = base / fixture
        _write(base / "with_skill" / "summary.json", with_doc)
        _write(base / "without_skill" / "summary.json", without_doc)

    def decided_pair(self, run, key="demo", dim="correctness", text="missed `Makefile` in src/app.py"):
        self.skill_pair(run, key,
                        _arm(1, 8.0, [(dim, 9, "fine")]),
                        _arm(1, 4.0, [(dim, 2, text)]), fixture=None)

    def analyze(self, **kw):
        return hjr.analyze(self.tree, self.evals, kw.get("min_recur", 2), kw.get("gap", 3.0))

    def test_judge_decided_pair_is_counted(self):
        self.decided_pair("20260801T100000Z")
        h = self.analyze()["headline"]
        self.assertEqual((h["pairs"], h["pairs_with_judge"], h["judge_decided"]), (1, 1, 1))
        self.assertEqual(h["by_kind"]["skill"]["decided"], 1)
        self.assertEqual(h["fixtures_with_judge_decided_pair"], 1)

    def test_pair_the_checks_separated_is_not_decided(self):
        self.skill_pair(TS, "demo", _arm(3, 8.0, [("correctness", 9, "a")]),
                        _arm(1, 4.0, [("correctness", 2, "b")]))
        h = self.analyze()["headline"]
        self.assertEqual((h["pairs_with_judge"], h["judge_decided"]), (1, 0))

    def test_small_overall_gap_is_not_decided(self):
        self.skill_pair(TS, "demo", _arm(1, 5.5, [("correctness", 9, "a")]),
                        _arm(1, 5.0, [("correctness", 2, "b")]))
        self.assertEqual(self.analyze()["headline"]["judge_decided"], 0)

    def test_recurrence_threshold(self):
        self.decided_pair("20260801T100000Z")
        self.assertEqual(self.analyze()["groups"], [])
        self.decided_pair("20260802T100000Z")
        groups = self.analyze()["groups"]
        self.assertEqual([(g["fixture"], g["dimension"], g["count"]) for g in groups],
                         [("demo", "correctness", 2)])
        self.assertEqual(self.analyze(min_recur=3)["groups"], [])

    def test_dimension_gap_filters_records(self):
        for run in ("20260801T100000Z", "20260802T100000Z"):
            self.skill_pair(run, "demo", _arm(1, 8.0, [("correctness", 6, "a")]),
                            _arm(1, 4.0, [("correctness", 5, "b")]))
        self.assertEqual(self.analyze()["groups"], [])

    def test_pairwise_fixture_is_excluded(self):
        self.decided_pair("20260801T100000Z")
        self.decided_pair("20260802T100000Z")
        fx = self.evals / "demo" / "fixture.yaml"
        fx.parent.mkdir(parents=True)
        fx.write_text("judge:\n  mode: pairwise\n", encoding="utf-8")
        result = self.analyze()
        self.assertEqual(result["headline"]["pairs"], 0)
        self.assertEqual(result["groups"], [])

    def test_guidance_pairing_and_existing_check_ids(self):
        fx = self.evals / "guidance" / "sec" / "case" / "fixture.yaml"
        fx.parent.mkdir(parents=True)
        fx.write_text("objective_checks:\n  - id: has-thing\n    type: file_exists\n",
                      encoding="utf-8")
        for run in ("20260801T100000Z", "20260802T100000Z"):
            base = self.tree / "results" / "guidance" / "sec" / run
            for arm, doc in (("with_guidance_full", _arm(1, 8.0, [("d", 9, "ok")])),
                             ("with_guidance_full_minus_section", _arm(1, 3.0, [("d", 1, "no `.github/x.yml`")]))):
                doc = dict(doc, fixture_name="case")
                _write(base / arm / "summary.json", doc)
        result = self.analyze()
        self.assertEqual(result["headline"]["by_kind"]["guidance"]["decided"], 2)
        (group,) = result["groups"]
        self.assertEqual(group["fixture"], "guidance/sec/case")
        self.assertEqual(group["existing_check_ids"], ["has-thing"])
        self.assertIn(".github/x.yml", [o["text"] for o in group["observables"]])

    def test_trials_pair_by_index(self):
        base = self.tree / "results" / "demo" / TS
        for arm, doc in (("with_skill", _arm(1, 8.0, [("d", 9, "a")])),
                         ("without_skill", _arm(1, 2.0, [("d", 1, "b")]))):
            for k in (1, 2):
                _write(base / arm / f"trial-{k}" / "summary.json", doc)
        self.assertEqual(self.analyze()["headline"]["judge_decided"], 2)

    def test_observables(self):
        got = hjr.observables("It ran `make test` but never touched docs/guide.md or run.sh.")
        self.assertEqual(got, {"make test", "docs/guide.md", "run.sh"})

    def test_report_has_proposal_line_and_main_writes_json(self):
        self.decided_pair("20260801T100000Z")
        self.decided_pair("20260802T100000Z")
        out = Path(self._tmp.name) / "out.json"
        self.assertIn(hjr.PROPOSAL_LINE, hjr.render(self.analyze()))
        self.assertEqual(hjr.main(["--results-tree", str(self.tree), "--evals", str(self.evals),
                                   "--json", str(out)]), 0)
        self.assertEqual(json.loads(out.read_text())["groups"][0]["count"], 2)

    def test_never_writes_under_evals(self):
        self.decided_pair("20260801T100000Z")
        self.decided_pair("20260802T100000Z")
        fx = self.evals / "demo" / "fixture.yaml"
        fx.parent.mkdir(parents=True)
        fx.write_text("objective_checks:\n  - id: a\n", encoding="utf-8")

        def snapshot():
            return {str(p): (p.read_bytes() if p.is_file() else None, p.stat().st_mtime_ns)
                    for p in sorted(self.evals.rglob("*"))}
        before = snapshot()
        hjr.main(["--results-tree", str(self.tree), "--evals", str(self.evals)])
        self.assertEqual(snapshot(), before)


if __name__ == "__main__":
    unittest.main()
