#!/usr/bin/env python3
"""skills-evals#555: the explorer's document-level `fires_without_results`.

A successful eval fire (routine-eval-fire.yml) at least two hours old is
delivered (a validated run of its cell came back), rejected (results came
back but none validated) or without results. Only fires on public,
non-private, scheduled fixtures count (`fire_scope`), and the summary carries
times and counts, never a name. The fire file is untrusted: a missing,
unreadable or out-of-bounds one makes the summary None (unknown), never 0.

Hermetic: a temporary evals/ tree in a throwaway Git index, invented run rows,
an injected wall clock and `fetched_at`. No network, no clock, no sleeps.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

import yaml

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

import explorer_data  # noqa: E402

WORKFLOW = ROOT / ".github" / "workflows" / "explorer-data.yml"
REG_URL = "https://github.com/Adam-S-Daniel/adam-agentskills"
PRIVATE_URL = explorer_data.plan_week.PRIVATE_REGISTRY_URL
#: A private skill name distinctive enough that any occurrence is a leak.
PRIVATE_NAME = "zz-private-distinct-tool"
NOW = datetime(2026, 10, 20, 12, 0, tzinfo=timezone.utc)
FETCHED = "2026-10-20T12:00:00Z"
AS_OF = "2026-10-20T12:00:00Z"
MODEL = "model-a"


def at(hours_ago: float) -> datetime:
    return NOW - timedelta(hours=hours_ago)


def iso(moment: datetime) -> str:
    return moment.strftime("%Y-%m-%dT%H:%M:%SZ")


def stamp(moment: datetime) -> str:
    return moment.strftime("%Y%m%dT%H%M%SZ")


def git(cwd: Path, *args: str) -> None:
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    env.update(GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL="/dev/null")
    subprocess.run(["git", "-c", "init.defaultBranch=main", *args], cwd=cwd, env=env,
                   check=True, capture_output=True)


class World:
    """A skills-evals checkout whose evals/ is in Git's index."""

    def __init__(self, test: unittest.TestCase):
        tmp = tempfile.TemporaryDirectory(prefix="fires-")
        test.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.repo = self.root / "skills-evals"
        self.evals = self.repo / "evals"
        self.evals.mkdir(parents=True)
        self.scheduled: list = []
        # A public skill, a fixture whose directory is not its skill's name,
        # a guidance section whose id equals a skill name, and a private one.
        self.fixture("pub/fx", skill="pub")
        self.fixture("odd-dir/fx", skill="col")
        self.fixture("guidance/pub/g1", subject="guidance", section="pub")
        self.fixture(f"{PRIVATE_NAME}/fx", skill=PRIVATE_NAME, registry=PRIVATE_URL)
        self.fixture("pub/unscheduled", skill="pub", scheduled=False)
        self.commit()

    def fixture(self, rel: str, scheduled: bool = True, **doc) -> None:
        d = self.evals / rel
        d.mkdir(parents=True)
        doc.setdefault("registry", REG_URL)
        (d / "fixture.yaml").write_text(yaml.safe_dump({"prompt": "invented", **doc}))
        if scheduled:
            self.scheduled.append(f"evals/{rel}")

    def commit(self) -> None:
        (self.evals / "scheduled.yml").write_text(yaml.safe_dump(
            {"fixtures": [{"path": p, "readiness": "invented"} for p in self.scheduled]}))
        if not (self.repo / ".git").exists():
            git(self.repo, "init", "-q")
        git(self.repo, "add", "-A")

    def scope(self, names=("pub", "col", PRIVATE_NAME), sections=("pub",)):
        return explorer_data.fire_scope(self.evals, set(names), set(sections))

    def summary(self, rel: str, doc: dict | None) -> Path | None:
        if doc is None:
            return None
        path = self.root / "tree" / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(doc))
        return path


_ids = iter(range(1000, 100000))


def fire(target: str, hours_ago: float = 5, model: str | None = MODEL, *, bare: bool = False,
         conclusion: str = "success", run_id: int | None = None) -> dict:
    title = "Fire eval routine: eval" + (" bare" if bare else "") + f" {target}" \
        + (f" {model}" if model else "")
    return {"id": next(_ids) if run_id is None else run_id, "display_title": title,
            "run_started_at": iso(at(hours_ago)), "conclusion": conclusion,
            "status": "completed"}


def record(skill: str, fixture, when: datetime, path: str, model: str = MODEL) -> dict:
    return {"skill": skill, "fixture": fixture, "model": model, "timestamp": stamp(when),
            "path": path}


EMPTY_INDEX = {"runs": [], "guidance_runs": [], "bare_runs": []}


def counts(world, runs, index=None, summaries=None, scope=None, fetched=FETCHED,
           wall=NOW, as_of=NOW):
    return explorer_data.fire_counts({"fetched_at": fetched, "runs": runs},
                                     index or EMPTY_INDEX, summaries or {},
                                     world.scope() if scope is None else scope, as_of, wall)


class ScopeTests(unittest.TestCase):

    def setUp(self):
        self.w = World(self)

    def test_scope_takes_the_subject_from_the_fixture_not_the_directory(self):
        self.assertEqual(self.w.scope(), {
            "evals/pub/fx": ("skill", "pub", "fx"),
            "evals/odd-dir/fx": ("skill", "col", "fx"),
            "evals/guidance/pub/g1": ("guidance", "pub", "g1")})

    def test_an_unlisted_skill_or_section_is_out(self):
        self.assertEqual(self.w.scope(names=(), sections=()), {})


class ClassificationTests(unittest.TestCase):

    def setUp(self):
        self.w = World(self)

    def test_delivered_rejected_and_without(self):
        delivered, rejected, without = fire("evals/pub/fx", 10), fire("evals/pub/fx", 6), \
            fire("evals/pub/fx", 3)
        index = {**EMPTY_INDEX, "runs": [record("pub", "fx", at(9.8),
                                                f"routine-results/R1/pub/{stamp(at(9.8))}")]}
        when = stamp(at(5.9))
        path = self.w.summary(f"routine-results/R2/pub/{when}/fx/with_skill/summary.json",
                              {"cross_model": {"model": MODEL}})
        summaries = {(f"routine-results/R2/pub/{when}", "pub", when, "fx", "with_skill"):
                     {"summary": path, "trials": []}}
        out = counts(self.w, [delivered, rejected, without], index, summaries)
        self.assertEqual(out, {"window_days": 14, "since": iso(at(10)), "counted": 3,
                               "without_results": 1, "rejected": 1,
                               "sweeps": [{"start": iso(at(3)), "end": iso(at(3)), "fires": 1}]})

    def test_a_run_outside_two_hours_after_the_fire_does_not_deliver_it(self):
        index = {**EMPTY_INDEX, "runs": [record("pub", "fx", at(7.5),
                                                f"routine-results/R1/pub/{stamp(at(7.5))}")]}
        self.assertEqual(counts(self.w, [fire("evals/pub/fx", 10)], index)["without_results"], 1)

    def test_another_models_run_does_not_deliver_it(self):
        index = {**EMPTY_INDEX, "runs": [record("pub", "fx", at(9.5), "results/pub/x",
                                                model="model-b")]}
        self.assertEqual(counts(self.w, [fire("evals/pub/fx", 10)], index)["without_results"], 1)

    def test_a_bare_run_never_delivers_a_fire(self):
        index = {**EMPTY_INDEX, "bare_runs": [record("pub", "fx", at(9.5), "results/pub/x")]}
        self.assertEqual(counts(self.w, [fire("evals/pub/fx", 10)], index)["without_results"], 1)

    def test_a_section_named_like_a_skill_does_not_collide(self):
        # A skill `pub` run of fixture g1 and a guidance `pub` run of fixture fx
        # share `skill` with the other subject; neither may deliver it.
        index = {**EMPTY_INDEX,
                 "runs": [record("pub", "g1", at(9.5), f"routine-results/R/pub/{stamp(at(9.5))}")],
                 "guidance_runs": [record("pub", "fx", at(9.5),
                                          f"routine-results/R/guidance/pub/{stamp(at(9.5))}")]}
        out = counts(self.w, [fire("evals/pub/fx", 10), fire("evals/guidance/pub/g1", 10)], index)
        self.assertEqual(out["without_results"], 2)
        index["runs"][0]["fixture"], index["guidance_runs"][0]["fixture"] = "fx", "g1"
        out = counts(self.w, [fire("evals/pub/fx", 10), fire("evals/guidance/pub/g1", 10)], index)
        self.assertEqual((out["without_results"], out["rejected"]), (0, 0))

    def test_a_guidance_folder_whose_summary_did_not_validate_is_rejected(self):
        # `_summaries` keys a guidance arm with no fixture; the name is in the
        # summary. This one has no `cross_model` ("no requested arm model").
        when = stamp(at(9.5))
        run_dir = f"routine-results/R/guidance/pub/{when}"

        def summaries(name):
            path = self.w.summary(f"{run_dir}-{name}/with/summary.json",
                                  {"subject": "guidance", "section": "pub",
                                   "fixture_name": name})
            return {(run_dir, "guidance/pub", when, None, "with"): {"summary": path,
                                                                     "trials": []}}

        out = counts(self.w, [fire("evals/guidance/pub/g1", 10)], summaries=summaries("g1"))
        self.assertEqual((out["without_results"], out["rejected"]), (0, 1))
        out = counts(self.w, [fire("evals/guidance/pub/g1", 10)], summaries=summaries("other"))
        self.assertEqual((out["without_results"], out["rejected"]), (1, 0))
        # An unreadable summary falls back to the section alone.
        unreadable = {(run_dir, "guidance/pub", when, None, "with"): {"summary": None,
                                                                       "trials": []}}
        out = counts(self.w, [fire("evals/guidance/pub/g1", 10)], summaries=unreadable)
        self.assertEqual(out["rejected"], 1)

    def test_a_rejected_skill_arm_of_another_model_is_not_this_fire(self):
        when = stamp(at(9.5))
        path = self.w.summary(f"routine-results/R/pub/{when}/fx/with_skill/summary.json",
                              {"cross_model": {"model": "model-b"}})
        summaries = {(f"routine-results/R/pub/{when}", "pub", when, "fx", "with_skill"):
                     {"summary": path, "trials": []}}
        out = counts(self.w, [fire("evals/pub/fx", 10)], summaries=summaries)
        self.assertEqual((out["without_results"], out["rejected"]), (1, 0))

    def test_a_results_folder_outside_routine_results_is_not_an_arrival(self):
        when = stamp(at(9.5))
        summaries = {(f"results/pub/{when}", "pub", when, "fx", "with_skill"):
                     {"summary": None, "trials": []}}
        self.assertEqual(counts(self.w, [fire("evals/pub/fx", 10)],
                                summaries=summaries)["rejected"], 0)

    def test_a_model_less_title_is_skipped(self):
        out = counts(self.w, [fire("evals/pub/fx", 10, model=None)])
        self.assertEqual((out["since"], out["without_results"]), (None, 0))

    def test_a_bare_fire_is_skipped(self):
        out = counts(self.w, [fire("evals/pub/fx", 10, bare=True)])
        self.assertEqual((out["since"], out["without_results"]), (None, 0))

    def test_an_unsuccessful_fire_is_skipped(self):
        out = counts(self.w, [fire("evals/pub/fx", 10, conclusion="failure")])
        self.assertEqual(out["without_results"], 0)

    def test_a_255_character_target_is_dropped(self):
        target = "evals/" + "a" * 249
        self.assertEqual(len(target), 255)
        self.assertIsNotNone(explorer_data.improve_outcomes.parse_title(
            fire(target)["display_title"]))
        self.assertEqual(counts(self.w, [fire(target, 10)])["without_results"], 0)

    def test_an_unscheduled_fixture_is_dropped(self):
        self.assertEqual(counts(self.w, [fire("evals/pub/unscheduled", 10)])["without_results"], 0)

    def test_the_window_bounds(self):
        out = counts(self.w, [fire("evals/pub/fx", 1.9), fire("evals/pub/fx", 14 * 24 + 1),
                              fire("evals/pub/fx", 2)])
        self.assertEqual((out["since"], out["without_results"]), (iso(at(2)), 1))

    def test_a_duplicate_row_counts_once(self):
        row = fire("evals/pub/fx", 10)
        self.assertEqual(counts(self.w, [row, dict(row)])["without_results"], 1)

    def test_untrusted_rows_of_any_shape_are_dropped(self):
        rows = [None, [], "x", {"display_title": 5}, {**fire("evals/pub/fx"), "id": "1"},
                {**fire("evals/pub/fx"), "run_started_at": "yesterday"}]
        self.assertEqual(counts(self.w, rows)["without_results"], 0)

    def test_sixty_minute_grouping(self):
        rows = [fire("evals/pub/fx", 10), fire("evals/pub/fx", 9), fire("evals/odd-dir/fx", 7.98),
                fire("evals/pub/fx", 5)]
        self.assertEqual(counts(self.w, rows)["sweeps"], [
            {"start": iso(at(10)), "end": iso(at(9)), "fires": 2},
            {"start": iso(at(7.98)), "end": iso(at(7.98)), "fires": 1},
            {"start": iso(at(5)), "end": iso(at(5)), "fires": 1}])


class UnknownTests(unittest.TestCase):

    def setUp(self):
        self.w = World(self)

    def test_a_missing_or_unreadable_file_is_unknown(self):
        self.assertIsNone(explorer_data.load_fire_runs(None))
        self.assertIsNone(explorer_data.load_fire_runs(self.w.root / "absent.json"))
        bad = self.w.root / "bad.json"
        for text in ("{not json", "[]", '{"fetched_at": "x"}', '{"pages": [{"no": 1}]}',
                     '{"pages": [[]]}'):
            bad.write_text(text)
            self.assertIsNone(explorer_data.load_fire_runs(bad), text)
        self.assertIsNone(explorer_data.fire_counts(None, EMPTY_INDEX, {}, self.w.scope(),
                                                    NOW, NOW))

    def test_a_good_file_loads_every_page(self):
        good = self.w.root / "good.json"
        good.write_text(json.dumps({"fetched_at": FETCHED, "pages": [
            {"total_count": 2, "workflow_runs": [fire("evals/pub/fx")]},
            {"total_count": 2, "workflow_runs": [fire("evals/odd-dir/fx")]}]}))
        loaded = explorer_data.load_fire_runs(good)
        self.assertEqual((loaded["fetched_at"], len(loaded["runs"])), (FETCHED, 2))

    def test_a_fetched_at_out_of_bounds_is_unknown(self):
        rows = [fire("evals/pub/fx", 10)]
        future = iso(NOW + timedelta(minutes=6))
        self.assertIsNone(counts(self.w, rows, fetched=future))
        self.assertIsNotNone(counts(self.w, rows, fetched=iso(NOW + timedelta(minutes=5))))
        stale = iso(NOW - timedelta(days=1, seconds=1))
        self.assertIsNone(counts(self.w, rows, fetched=stale))
        for junk in (None, "", "2026-10-20T12:00:00", "tomorrow", 1700000000):
            self.assertIsNone(counts(self.w, rows, fetched=junk), junk)


class DocumentTests(unittest.TestCase):
    """build + finish: the public document."""

    def build(self, w: World, fire_runs, wall=NOW):
        tree = w.root / "tree"
        (tree / "coverage").mkdir(parents=True, exist_ok=True)
        (tree / "coverage" / "latest.json").write_text(json.dumps({
            "publication": {"as_of": AS_OF},
            "registries": [
                {"name": "adam-agentskills", "private": False,
                 "counts": {"covered": 2, "skipped": 0, "gap": 0, "total": 2},
                 "skills": [{"skill": "pub", "status": "covered"},
                            {"skill": "col", "status": "covered"}]},
                {"name": "adam-agentskills-private", "private": True,
                 "skills": [{"skill": PRIVATE_NAME, "status": "covered"}]}]}))
        roster = w.root / "roster.yml"
        roster.write_text(yaml.safe_dump({"arms": [{"id": MODEL}], "judge": {"id": "model-j"}}))
        doc = explorer_data.build(
            tree, roster, ROOT / "evals" / "gate-policy.yml", w.evals, AS_OF, "a" * 40, "b" * 40,
            manifest=[{"id": "pub", "heading": "Pub", "status": "covered"}],
            fire_runs=fire_runs, wall_clock=wall)
        return doc, explorer_data.finish(doc)

    @staticmethod
    def unfiltered(evals_dir, _skill_names, _section_ids):
        """The SCOPE FILTER switched off: every scheduled fixture counts."""
        sched = yaml.safe_load((evals_dir / "scheduled.yml").read_text())
        out = {}
        for row in sched["fixtures"]:
            doc = yaml.safe_load((evals_dir.parent / row["path"] / "fixture.yaml").read_text())
            parts = row["path"].split("/")
            out[row["path"]] = (("guidance", doc["section"], parts[3])
                                if doc.get("subject") == "guidance"
                                else ("skill", doc["skill"], parts[2]))
        return out

    def fires(self):
        return {"fetched_at": FETCHED,
                "runs": [fire("evals/pub/fx", 10), fire(f"evals/{PRIVATE_NAME}/fx", 9)]}

    def test_a_private_fire_is_not_counted(self):
        doc, text = self.build(World(self), self.fires())
        self.assertEqual(doc["fires_without_results"]["without_results"], 1)
        self.assertEqual(doc["fires_without_results"]["sweeps"],
                         [{"start": iso(at(10)), "end": iso(at(10)), "fires": 1}])
        self.assertNotIn(PRIVATE_NAME, text)
        self.assertNotIn("evals/", json.dumps(doc["fires_without_results"]))

    def test_negative_control_the_private_fire_counts_unfiltered(self):
        with mock.patch.object(explorer_data, "fire_scope", self.unfiltered):
            doc, _text = self.build(World(self), self.fires())
        self.assertEqual(doc["fires_without_results"]["without_results"], 2)

    def test_no_file_is_unknown_in_the_document(self):
        doc, _text = self.build(World(self), None)
        self.assertIsNone(doc["fires_without_results"])

    def test_byte_identical_whatever_the_wall_clock(self):
        first = self.build(World(self), self.fires(), wall=NOW)[1]
        later = self.build(World(self), self.fires(), wall=NOW + timedelta(days=400))[1]
        self.assertEqual(first, later)

    def test_a_future_fetched_at_is_unknown_in_the_document(self):
        runs = {**self.fires(), "fetched_at": iso(NOW + timedelta(hours=1))}
        doc, _text = self.build(World(self), runs, wall=NOW)
        self.assertIsNone(doc["fires_without_results"])


class WorkflowTests(unittest.TestCase):
    """explorer-data.yml, parsed with the `yaml` module."""

    @classmethod
    def setUpClass(cls):
        cls.wf = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))
        cls.build = cls.wf["jobs"]["build"]
        cls.fetch = next(s for s in cls.build["steps"]
                         if s.get("name") == "List the recent eval fires")

    def test_actions_read_only_on_build(self):
        self.assertEqual(self.wf["permissions"], {})
        # The fixture queue (2026-11-03) adds `pull-requests: read`.
        self.assertEqual(self.build["permissions"],
                         {"actions": "read", "contents": "read", "issues": "read",
                          "pull-requests": "read"})
        self.assertEqual(self.wf["jobs"]["publish"]["permissions"], {"contents": "write"})

    def test_the_token_is_only_in_the_fetching_steps(self):
        self.assertNotIn("env", self.wf)
        for job in self.wf["jobs"].values():
            self.assertNotIn("env", job)
        holders = {s.get("name") for job in self.wf["jobs"].values() for s in job["steps"]
                   if any(k in (s.get("env") or {}) for k in ("GH_TOKEN", "GITHUB_TOKEN"))}
        # The regression-issue listing predates #555; publish pushes with its own;
        # the fixture queue (2026-11-03) lists and files issues with its own.
        self.assertEqual(holders, {"List the recent eval fires", "List the open regression issues",
                                   "Commit to persistent/eval-results and push",
                                   "List the fixture requests and their pull requests",
                                   "File, keep or close the fixture queue issues",
                                   # The lessons (2026-11-03): public listings.
                                   "List the skill draft pull requests",
                                   "List the memory promotion and skill proposal issues",
                                   # The public data contract (2026-11-04): public listings.
                                   "List the public repositories",
                                   "List recent activity in the public repositories",
                                   "List the lesson outcomes",
                                   # check-site (2026-11-04): lists and dispatches
                                   # site-freshness.yml runs, no data.
                                   "Dispatch the site freshness check when it is due"})
        self.assertEqual(self.fetch["env"], {"GH_TOKEN": "${{ github.token }}"})

    def test_the_fetch_step_cannot_fail_the_job(self):
        self.assertIs(self.fetch.get("continue-on-error"), True)
        run = self.fetch["run"]
        self.assertNotIn("set -e", run)
        self.assertEqual(run.strip().splitlines()[-1], "exit 0")
        self.assertIn('rm -f "$out" "$out.tmp"', run)

    def test_the_fetch_step_prints_only_a_fixed_line(self):
        run = self.fetch["run"]
        self.assertNotIn("${{", run)
        printing = [line.strip() for line in run.splitlines()
                    if line.strip().split(" ", 1)[0] in ("echo", "cat", "printf", "jq")]
        self.assertEqual(printing, ['echo "fire runs unavailable (exit $rc)"'])
        self.assertIn("date -u -d '14 days ago' +%Y-%m-%dT%H:%M:%SZ", run)
        self.assertLess(run.index("fetched_at=$(date -u"), run.index("gh api"))
        self.assertIn('-f "created=>=$since"', run)

    def test_the_build_step_reads_the_fire_file(self):
        step = next(s for s in self.build["steps"] if s.get("name") == "Build the explorer data")
        self.assertIn('--fire-runs "$RUNNER_TEMP/fire-runs.json"', step["run"])
        names = [s.get("name") for s in self.build["steps"]]
        self.assertLess(names.index("List the recent eval fires"),
                        names.index("Build the explorer data"))


if __name__ == "__main__":
    unittest.main()
