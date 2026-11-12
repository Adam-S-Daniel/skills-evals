#!/usr/bin/env python3
"""Weekly spend totals: the `claude/spend-<timestamp>` ingest lane.

The private dashboard refresh (`dashboard/build.py --spend`) pushes
`claude/spend-<YYYYMMDDTHHMMSSZ>` adding exactly `spend/weekly.json` in
explorer/schema.json's `$defs.spend_file` shape. `spend-pushed.yml` only
signals; `routine-eval-ingest.yml` (default branch copy) judges the branch
with `ingest_routine_results.validate_spend` and writes the file to
`persistent/eval-results` at `spend/weekly.json`, where
`explorer_public.build_spend` reads it when evals/public-export.yml
`include_spend` is true. What is pinned here, mirroring the cost lane's
tests in test_issue_routine_eval_ingest.py:

  * the branch adds exactly one regular file at exactly `spend/weekly.json`,
    under the size cap, valid against `$defs.spend_file`, weekly totals only
    (no key outside SPEND_KEYS / SPEND_WEEK_KEYS, Monday weeks, no repeat,
    a plain plan name, no session/thread/message/trigger id or `@`), and
    every rejection stages nothing and never quotes the content;
  * `resolve` names `kind=spend` for the branch, and no eval or cost name
    is ever a spend name, and back;
  * `place --kind spend` replaces an older file, keeps a newer one
    (`stale=true`, exit 0) and refuses a non-file destination;
  * the signal workflow is a filtered push with no reach that no other push
    workflow shares, the ingest listens for it, and the ingest wakes
    explorer-data.yml, whose builder reads the placed file.

Fixtures are built in-test in temporary git repositories. Hermetic.
"""

from __future__ import annotations

import contextlib
import copy
import io
import json
import os
import shutil
import sys
import tempfile
import unittest
from fnmatch import fnmatch
from pathlib import Path

TEST_DIR = Path(__file__).resolve().parent
REPO_ROOT = TEST_DIR.parent.parent
sys.path.insert(0, str(TEST_DIR))
sys.path.insert(0, str(REPO_ROOT / "scripts"))
sys.path.insert(0, str(REPO_ROOT / "harness"))

from test_issue_routine_eval_ingest import (  # noqa: E402
    INGEST, MARKER, SPEND_SIGNAL, WORKFLOWS, GitCase, load, triggers)

import explorer_public  # noqa: E402
import ingest_routine_results as ingest  # noqa: E402

STAMP = "20261104T120000Z"
SPEND_BRANCH = f"claude/spend-{STAMP}"
SCHEMA = REPO_ROOT / "explorer" / "schema.json"
EXPLORER_DATA = WORKFLOWS / "explorer-data.yml"


def spend_doc(**changes) -> dict:
    """A file in the shape dashboard/build.py's spend_file writes."""
    doc = {"schema": 1, "generated_at": "2026-11-04T12:00:00Z", "plan": "Max 20x",
           "weeks": [
               {"week": "2026-10-26", "eval_runs": 12, "plan_meter_points": 31.25,
                "api_usd": 40.125, "thread_spend_usd": 18.5, "cost_per_verdict": None},
               {"week": "2026-11-02", "eval_runs": 3, "plan_meter_points": 7.0,
                "api_usd": 9.75, "thread_spend_usd": 4.0, "run_usd": 1.3333333333333333,
                "plan": "Max 20x"}]}
    doc.update(changes)
    return doc


def spend_bytes(doc: dict) -> bytes:
    return json.dumps(doc, indent=1).encode("utf-8")


class SpendBranchTests(GitCase):

    def setUp(self):
        super().setUp()
        self.git("checkout", "-q", "main")
        self.git("checkout", "-q", "-b", SPEND_BRANCH)

    def validate_spend(self, branch=SPEND_BRANCH):
        return ingest.validate_spend(str(self.repo), "main", branch, branch, None,
                                     self.tmp / "staged", SCHEMA)

    def assertSpendRejected(self, pattern):
        with self.assertRaisesRegex(ingest.Rejected, pattern) as caught:
            self.validate_spend()
        self.assertNotIn(MARKER, str(caught.exception))
        staged = self.tmp / "staged"
        self.assertFalse(staged.exists() and any(p.is_file() for p in staged.rglob("*")),
                         "a rejected branch stages nothing")

    def test_accepts_the_file_and_stages_its_exact_bytes(self):
        data = spend_bytes(spend_doc())
        sha = self.commit({ingest.SPEND_SOURCE: data})
        result = self.validate_spend()
        self.assertEqual(result, {"run_id": STAMP, "sha": sha, "files": "1"})
        self.assertEqual((self.tmp / "staged" / ingest.SPEND_DEST).read_bytes(), data)
        self.assertEqual([p for p in (self.tmp / "staged").rglob("*") if p.is_file()],
                         [self.tmp / "staged" / ingest.SPEND_DEST])

    def test_a_total_in_the_dashboards_shape_is_accepted(self):
        # The shape dashboard/build.py's spend_file writes (#980): since the
        # first week, over the decided verdicts, split into its three parts.
        total = {"since": "2026-10-19", "verdicts": 12, "usd": 5541.65, "run_usd": 991.75,
                 "thread_spend_usd": 4335.49, "api_usd": 214.41, "cost_per_verdict": 461.8}
        doc = spend_doc(total=total)
        doc["weeks"] = [{k: v for k, v in w.items() if k != "cost_per_verdict"} | {"run_usd": 1.0}
                        for w in doc["weeks"]]
        data = spend_bytes(doc)
        self.commit({ingest.SPEND_SOURCE: data})
        self.validate_spend()
        self.assertEqual((self.tmp / "staged" / ingest.SPEND_DEST).read_bytes(), data)

    def test_a_minimal_file_is_accepted(self):
        self.commit({ingest.SPEND_SOURCE: spend_bytes(
            {"schema": 1, "generated_at": "2026-11-04T12:00:00Z", "weeks": []})})
        self.assertEqual(self.validate_spend()["files"], "1")

    def test_rejects_a_second_file(self):
        self.commit({ingest.SPEND_SOURCE: spend_bytes(spend_doc()),
                     "spend/sessions.json": b"{}\n"})
        self.assertSpendRejected("exactly one file")

    def test_rejects_a_wrong_path(self):
        for path in ("spend/weekly-2.json", "spend.json", f"spend/{STAMP}/weekly.json",
                     f"eval-results/{STAMP}/weekly.json", "explorer/latest.json"):
            with self.subTest(path=path):
                self.git("checkout", "-q", "main")
                self.git("checkout", "-q", "-B", SPEND_BRANCH)
                self.commit({path: spend_bytes(spend_doc())})
                self.assertSpendRejected("not 'spend/weekly.json'")

    def test_rejects_a_modified_main_file(self):
        self.commit({"README.md": spend_bytes(spend_doc())})
        self.assertSpendRejected("only additions")

    def test_rejects_an_executable_bit(self):
        self.write({ingest.SPEND_SOURCE: spend_bytes(spend_doc())})
        os.chmod(self.repo / ingest.SPEND_SOURCE, 0o755)
        self.git("add", "-A")
        self.git("commit", "-q", "-m", "spend")
        self.assertSpendRejected("mode 100755")

    def test_rejects_an_oversized_file(self):
        self.commit({ingest.SPEND_SOURCE: spend_bytes(spend_doc()) + b" " * ingest.SPEND_CAP})
        self.assertSpendRejected("over the")

    def test_rejects_per_session_per_thread_and_id_fields(self):
        week = dict(spend_doc()["weeks"][0])
        cases = {
            "top-level sessions": spend_doc(sessions=[{"cost": 1}]),
            "top-level thread rows": spend_doc(threads={"x": 1}),
            "a week's session id": spend_doc(weeks=[{**week, "session_id": MARKER}]),
            "a week's thread rows": spend_doc(weeks=[{**week, "threads": [MARKER]}]),
            "a week's per-thread spend": spend_doc(weeks=[{**week, "thread": 1.0}]),
        }
        for label, doc in cases.items():
            with self.subTest(label):
                self.git("checkout", "-q", "main")
                self.git("checkout", "-q", "-B", SPEND_BRANCH)
                self.commit({ingest.SPEND_SOURCE: spend_bytes(doc)})
                self.assertSpendRejected("not a weekly total")

    def test_rejects_a_field_in_the_total_that_is_not_a_total(self):
        self.commit({ingest.SPEND_SOURCE: spend_bytes(
            spend_doc(total={"since": "2026-10-19", "threads": [MARKER]}))})
        self.assertSpendRejected("the total carries")

    def test_rejects_ids_and_addresses_in_values(self):
        for label, plan, pattern in (
                ("thread id", "thread_Ab12Cd34", "trigger id"),
                ("session id", "cse_0123456789", "trigger id"),
                ("address", "owner@example.com", "plan name"),
                ("long", "x" * 41, "plan name")):
            with self.subTest(label):
                self.git("checkout", "-q", "main")
                self.git("checkout", "-q", "-B", SPEND_BRANCH)
                self.commit({ingest.SPEND_SOURCE: spend_bytes(spend_doc(plan=plan))})
                self.assertSpendRejected(pattern)
        # The id backstop on the whole text, reached directly.
        for text in ('{"thread_Ab12Cd34": 1}', '"session_x"', '"a@b"'):
            with self.subTest(text=text), self.assertRaises(ingest.Rejected):
                ingest.check_spend(spend_doc(), text, "'spend/weekly.json'")

    def test_rejects_schema_breaches_without_quoting_them(self):
        week = dict(spend_doc()["weeks"][0])
        for label, doc in {
                "schema version": spend_doc(schema=2),
                "no weeks": {"schema": 1, "generated_at": "2026-11-04T12:00:00Z"},
                "negative dollars": spend_doc(weeks=[{**week, "api_usd": -1}]),
                "string count": spend_doc(weeks=[{**week, "eval_runs": MARKER}]),
                "bad stamp": spend_doc(generated_at=MARKER),
                "bad week": spend_doc(weeks=[{**week, "week": MARKER}]),
                "no week": spend_doc(weeks=[{k: v for k, v in week.items() if k != "week"}]),
                }.items():
            with self.subTest(label):
                self.git("checkout", "-q", "main")
                self.git("checkout", "-q", "-B", SPEND_BRANCH)
                self.commit({ingest.SPEND_SOURCE: spend_bytes(doc)})
                self.assertSpendRejected(r"does not match \$defs\.spend_file")

    def test_rejects_weeks_that_are_not_distinct_mondays_and_a_missing_stamp(self):
        week = dict(spend_doc()["weeks"][0])
        for label, doc, pattern in (
                ("tuesday", spend_doc(weeks=[{**week, "week": "2026-10-27"}]), "Monday"),
                ("not a date", spend_doc(weeks=[{**week, "week": "2026-13-02"}]), "not a date"),
                ("repeat", spend_doc(weeks=[week, week]), "repeats"),
                ("no stamp", {k: v for k, v in spend_doc().items() if k != "generated_at"},
                 "no generated_at")):
            with self.subTest(label):
                self.git("checkout", "-q", "main")
                self.git("checkout", "-q", "-B", SPEND_BRANCH)
                self.commit({ingest.SPEND_SOURCE: spend_bytes(doc)})
                self.assertSpendRejected(pattern)

    def test_rejects_duplicate_keys_and_non_finite_numbers(self):
        good = spend_bytes(spend_doc()).decode()
        for label, text in (("duplicate", good.replace('"schema": 1', '"schema": 1, "schema": 1')),
                            ("nan", good.replace("31.25", "NaN"))):
            with self.subTest(label):
                self.git("checkout", "-q", "main")
                self.git("checkout", "-q", "-B", SPEND_BRANCH)
                self.commit({ingest.SPEND_SOURCE: text.encode()})
                with self.assertRaises(ingest.Rejected):
                    self.validate_spend()

    def test_rejects_bad_branch_names(self):
        self.commit({ingest.SPEND_SOURCE: spend_bytes(spend_doc())})
        for bad in (SPEND_BRANCH + "-x", "claude/spend-", "claude/spend-20261104",
                    f"claude/eval-spend-{STAMP}", f"claude/eval-{STAMP}-abcdef",
                    SPEND_BRANCH.lower()):
            with self.subTest(bad=bad), self.assertRaisesRegex(ingest.Rejected, "claude/spend-"):
                ingest.validate_spend(str(self.repo), "main", "HEAD", bad, None,
                                      self.tmp / "staged", SCHEMA)

    def test_rejects_a_moved_branch(self):
        self.commit({ingest.SPEND_SOURCE: spend_bytes(spend_doc())})
        with self.assertRaisesRegex(ingest.Rejected, "moved"):
            ingest.validate_spend(str(self.repo), "main", SPEND_BRANCH, SPEND_BRANCH,
                                  "0" * 40, self.tmp / "staged", SCHEMA)

    def test_main_validate_prints_kind_and_dest_and_a_rejection_is_red(self):
        self.commit({ingest.SPEND_SOURCE: spend_bytes(spend_doc())})
        schema = self.repo / "explorer" / "schema.json"
        schema.parent.mkdir()
        shutil.copy(SCHEMA, schema)  # main's copy, as the workflow's checkout has it
        argv = ["validate", "--repo", str(self.repo), "--base", "main",
                "--source", SPEND_BRANCH, "--branch", SPEND_BRANCH,
                "--out", str(self.tmp / "staged")]
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            self.assertEqual(ingest.main(argv), 0)
        lines = dict(line.split("=", 1) for line in out.getvalue().splitlines())
        self.assertEqual((lines["kind"], lines["dest"], lines["run_id"]),
                         ("spend", "spend/weekly.json", STAMP))
        self.commit({"spend/extra.json": b"{}\n"})
        shutil.rmtree(self.tmp / "staged")
        err = io.StringIO()
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(err):
            self.assertEqual(ingest.main(argv), 1)
        self.assertIn("rejected:", err.getvalue())

    def test_the_id_and_plan_patterns_are_the_explorers(self):
        self.assertEqual(ingest.FORBIDDEN_ID_RE.pattern,
                         explorer_public.FORBIDDEN_ID_RE.pattern)
        self.assertEqual(ingest.PLAN_RE.pattern, explorer_public._PLAN_RE.pattern)
        # The ingest still accepts the retired per-verdict week field, so a file
        # from a dashboard build older than the total is not rejected.
        self.assertEqual(ingest.SPEND_WEEK_KEYS, set(explorer_public.SPEND_WEEK_KEYS) | {"cost_per_verdict"})
        self.assertEqual(ingest.SPEND_TOTAL_KEYS, set(explorer_public.SPEND_TOTAL_KEYS))
        schema = json.loads(SCHEMA.read_text(encoding="utf-8"))["$defs"]["spend_file"]
        self.assertEqual(ingest.SPEND_KEYS, set(schema["properties"]))
        self.assertEqual(ingest.SPEND_WEEK_KEYS, set(schema["properties"]["weeks"]
                                                     ["items"]["properties"]))


class SpendResolveAndPlaceTests(unittest.TestCase):

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp)

    def event(self, branch) -> str:
        path = self.tmp / "event.json"
        path.write_text(json.dumps({"inputs": {"branch": branch}}), encoding="utf-8")
        return str(path)

    def test_resolve_names_the_kind_and_never_confuses_it(self):
        self.assertEqual(ingest.resolve_ingest("workflow_dispatch", self.event(SPEND_BRANCH)),
                         {"branch": SPEND_BRANCH, "sha": "", "run_id": STAMP, "kind": "spend"})
        run_id = "20261006T194256Z-f944ea"
        for branch, kind in ((f"claude/eval-{run_id}", "eval"),
                             (f"claude/eval-cost-{run_id}", "cost")):
            self.assertEqual(ingest.resolve_ingest("workflow_dispatch", self.event(branch))["kind"],
                             kind)
            self.assertIsNone(ingest.SPEND_BRANCH_RE.fullmatch(branch))
        for pattern in (ingest.BRANCH_RE, ingest.COST_BRANCH_RE):
            self.assertIsNone(pattern.fullmatch(SPEND_BRANCH))
        for bad in (SPEND_BRANCH + "-x", f"claude/eval-spend-{STAMP}"):
            with self.assertRaises(ingest.Rejected):
                ingest.resolve_ingest("workflow_dispatch", self.event(bad))

    def stage(self, doc: dict) -> Path:
        staged = self.tmp / "staged"
        (staged / "spend").mkdir(parents=True, exist_ok=True)
        (staged / ingest.SPEND_DEST).write_bytes(spend_bytes(doc))
        return staged

    def place(self, staged: Path, tree: Path) -> tuple[int, list[str]]:
        out = io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(io.StringIO()):
            code = ingest.main(["place", "--staged", str(staged), "--tree", str(tree),
                                "--kind", "spend"])
        return code, out.getvalue().splitlines()

    def test_latest_generated_wins_and_an_older_file_is_stale(self):
        tree = self.tmp / "tree"
        target = tree / ingest.SPEND_DEST
        older = spend_doc(generated_at="2026-11-01T00:00:00Z")
        newer = spend_doc(generated_at="2026-11-04T12:00:00Z")
        # First file: written.
        code, lines = self.place(self.stage(older), tree)
        self.assertEqual((code, "changed=true" in lines), (0, True))
        # A newer one replaces it.
        shutil.rmtree(self.tmp / "staged")
        code, lines = self.place(self.stage(newer), tree)
        self.assertEqual((code, "changed=true" in lines), (0, True))
        self.assertEqual(target.read_bytes(), spend_bytes(newer))
        # The same bytes again: nothing to commit.
        code, lines = self.place(self.tmp / "staged", tree)
        self.assertEqual((code, "changed=false" in lines, "stale=true" in lines),
                         (0, True, False))
        # An older one (a re-dispatched old branch) never rolls it back.
        shutil.rmtree(self.tmp / "staged")
        code, lines = self.place(self.stage(older), tree)
        self.assertEqual((code, "stale=true" in lines, "changed=false" in lines), (0, True, True))
        self.assertEqual(target.read_bytes(), spend_bytes(newer))
        # Without --kind spend the same difference is the eval rule: rejected.
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(ingest.main(["place", "--staged", str(self.tmp / "staged"),
                                          "--tree", str(tree)]), 1)

    def test_a_directory_or_symlink_in_the_way_is_refused(self):
        tree = self.tmp / "tree"
        (tree / ingest.SPEND_DEST).mkdir(parents=True)
        code, _ = self.place(self.stage(spend_doc()), tree)
        self.assertEqual(code, 1)
        other = self.tmp / "other"
        other.mkdir()
        linked = self.tmp / "linked"
        linked.mkdir()
        (linked / "spend").symlink_to(other)
        code, _ = self.place(self.tmp / "staged", linked)
        self.assertEqual(code, 1)
        self.assertEqual(list(other.iterdir()), [])

    def test_the_placed_file_is_what_the_explorer_publishes(self):
        tree = self.tmp / "tree"
        doc = spend_doc()
        self.assertEqual(self.place(self.stage(doc), tree)[0], 0)
        built = explorer_public.build_spend(tree, True)
        self.assertEqual(built["generated_at"], doc["generated_at"])
        self.assertEqual([w["week"] for w in built["weeks"]], ["2026-11-02", "2026-10-26"])
        self.assertEqual(built["weeks"][0]["run_usd"], 1.3333333333333333)
        self.assertEqual(built["weeks"][1]["plan"], "Max 20x")
        self.assertIsNone(explorer_public.build_spend(tree, False))


def fires(branches, branch) -> bool:
    """GitHub's filter: a branch triggers when it matches a positive pattern
    and the LAST matching pattern is not a `!` one."""
    hit = False
    for pattern in branches:
        if fnmatch(branch, pattern.lstrip("!")):
            hit = not pattern.startswith("!")
    return hit


class SpendWorkflowTests(unittest.TestCase):

    def test_signal_is_a_filtered_push_with_no_reach(self):
        doc = load(SPEND_SIGNAL)
        on = triggers(doc)
        self.assertEqual(set(on), {"push"})
        self.assertEqual(on["push"]["branches"], ["claude/spend-*"])
        self.assertEqual(on["push"]["paths"],
                         [f"{ingest.SPEND_SOURCE.rsplit('/', 1)[0]}/**"])
        self.assertEqual(doc["permissions"], {})
        for job in doc["jobs"].values():
            self.assertNotIn("permissions", job)
            for step in job["steps"]:
                self.assertNotIn("uses", step, "the signal checks nothing out")

    def test_no_other_push_workflow_shares_a_spend_push(self):
        spend_on = triggers(load(SPEND_SIGNAL))["push"]
        self.assertTrue(fires(spend_on["branches"], SPEND_BRANCH))
        run_id = "20261006T194256Z-f944ea"
        for branch in (f"claude/eval-{run_id}", f"claude/eval-cost-{run_id}",
                       f"claude/eval-improve-{run_id}", f"claude/scaffold-{run_id}"):
            self.assertFalse(fires(spend_on["branches"], branch), branch)
        for other in sorted(WORKFLOWS.glob("*.yml")):
            if other == SPEND_SIGNAL:
                continue
            push = (triggers(load(other)) or {}).get("push")
            if not isinstance(push, dict) or "branches" not in push:
                continue  # unfiltered pushes are main-only workflows below
            with self.subTest(other=other.name):
                self.assertFalse(fires(push["branches"], SPEND_BRANCH)
                                 and ("paths" not in push or any(
                                     fnmatch(ingest.SPEND_SOURCE, p) for p in push["paths"])))
        # Negative control on the matcher itself.
        self.assertTrue(fires(["claude/*"], SPEND_BRANCH))

    def test_the_ingest_listens_and_wakes_the_explorer(self):
        on = triggers(load(INGEST))["workflow_run"]
        self.assertIn(load(SPEND_SIGNAL)["name"], on["workflows"])
        self.assertTrue(any(fnmatch(SPEND_BRANCH, p) for p in on["branches"]))
        explorer = triggers(load(EXPLORER_DATA))["workflow_run"]
        self.assertIn(load(INGEST)["name"], explorer["workflows"])
        self.assertEqual(explorer["types"], ["completed"])
        self.assertNotIn("branches", explorer, "a spend ingest must wake it too")

    def test_the_signal_is_locked(self):
        lock = (WORKFLOWS / "actions.lock").read_text(encoding="utf-8")
        self.assertIn(f"'.github/workflows/{SPEND_SIGNAL.name}': []", lock)

    def test_the_week_key_guard_can_fail(self):
        # Negative control: a per-session row passes the schema alone
        # (spend_file allows extra keys), so check_spend is what stops it.
        import jsonschema  # noqa: PLC0415
        schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
        doc = copy.deepcopy(spend_doc())
        doc["weeks"][0]["session_id"] = "x"
        jsonschema.Draft202012Validator(schema["$defs"]["spend_file"]).validate(doc)
        with self.assertRaisesRegex(ingest.Rejected, "not a weekly total"):
            ingest.check_spend(doc, json.dumps(doc), "'spend/weekly.json'")


if __name__ == "__main__":
    unittest.main()
