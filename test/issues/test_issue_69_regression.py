#!/usr/bin/env python3
"""Issues #69 and #121: regression detection and its issue lifecycle.

harness/regression.py decides, per cell (subject, id, fixture, model, pair),
whether a skill or guidance section stopped helping between two windows of
runs; scripts/regression_issue.py keeps one `Regression:` issue per subject.
Adam asked on 2026-10-31 that regression detection be finished; the
committed thresholds are starting values.

Hermetic: run records built here in the shape compute_gates.build_index
returns, a fake `gh`, a fake or local-only `git`; no network, no clock.
"""

from __future__ import annotations

import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stderr
from pathlib import Path
from unittest import mock

import yaml

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "harness"))
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "test"))

from lockfile_pins import lock_problem  # noqa: E402
import compute_gates  # noqa: E402
import gates  # noqa: E402
import regression  # noqa: E402
import regression_issue  # noqa: E402
import retire_skill  # noqa: E402

BOT = "github-actions[bot]"
SONNET, OPUS = "claude-sonnet-5-5", "claude-opus-5-5"
MODELS = [OPUS, SONNET]
AS_OF = "20261031T000000Z"
POLICY = {"window_runs": 3, "min_window_runs": 2, "objective_drop": 0.15,
          "judge_drop": 1.0, "lost_delta_min_previous": 0.10}
POLICIES = {"skills": dict(POLICY), "guidance": dict(POLICY)}


def trial(passed: int, judge=None, total: int = 4) -> dict:
    """One trial, shaped by gates.trial_record from a trial summary."""
    summary = {"objective_checks": [{"id": f"c{i}", "passed": i < passed}
                                    for i in range(total)]}
    if judge is not None:
        summary["judge"] = {"overall": judge}
    return gates.trial_record(summary)


def stamp(day: int) -> str:
    return f"202610{day:02d}T000000Z"


def run(ident, role, day, passed, *, judge=None, model=SONNET, fixture=None, pair=None,
        tested="t1", fixture_digest="f1", context="ctx", cli=("1.0",)) -> dict:
    record = {"skill": ident, "fixture": fixture, "model": model, "role": role,
              "timestamp": stamp(day), "path": f"results/{ident}/{stamp(day)}",
              "report": f"results/{ident}/{stamp(day)}/report.md",
              "tested_digest": tested, "fixture_digest": fixture_digest,
              "arm_context_digest": context, "pair_key": context,
              "cli_versions": list(cli), "run": 1,
              "judge_conditional": judge is None, "judge_carried": False,
              "fixture_checks": True, "trials": [trial(passed, judge)]}
    if pair is not None:
        record["pair"] = pair
    return record


def series(ident, with_passed, without_passed=(), *, judge=None, first=1, **kw) -> list:
    """Runs on consecutive days: `with` arms from `with_passed` (checks passed
    of 4), `without` arms from `without_passed`; `judge` a list for `with`."""
    judges = judge or [None] * len(with_passed)
    return ([run(ident, "with", first + i, p, judge=j, **kw)
             for i, (p, j) in enumerate(zip(with_passed, judges))]
            + [run(ident, "without", first + i, p, **kw)
               for i, p in enumerate(without_passed)])


def index_of(runs=(), guidance=(), bare=()) -> dict:
    return {"runs": list(runs), "guidance_runs": list(guidance), "bare_runs": list(bare),
            "skipped": {}, "skills": [], "sections": []}


def verdict_of(runs, policies=POLICIES, guidance=False, **index) -> dict:
    """The one row of a one-cell index."""
    doc = regression.compute(index_of(guidance=runs) if guidance else index_of(runs),
                             MODELS, policies, AS_OF)
    assert len(doc["rows"]) == 1, doc["rows"]
    return doc["rows"][0]


class VerdictTests(unittest.TestCase):
    def test_regressed_on_the_objective(self):
        row = verdict_of(series("a", [4, 4, 4, 2, 2, 2]))
        self.assertEqual(row["verdict"], "regressed")
        self.assertEqual(row["numbers"]["objective"],
                         {"previous": 1.0, "current": 0.5, "change": -0.5, "noise": 0.0})
        self.assertIn("objective", row["reason"])

    def test_regressed_on_the_judge_alone(self):
        row = verdict_of(series("a", [4] * 6, judge=[8, 8, 8, 6, 6, 6]))
        self.assertEqual(row["verdict"], "regressed")
        self.assertIn("judge", row["reason"])
        self.assertEqual(row["numbers"]["judge"]["change"], -2.0)

    def test_lost_delta_when_the_without_arm_caught_up(self):
        row = verdict_of(series("a", [4] * 6, [2, 2, 2, 4, 4, 4]))
        self.assertEqual(row["verdict"], "lost-delta")
        self.assertEqual(row["numbers"]["delta"], {"previous": 0.5, "current": 0.0})

    def test_lost_delta_needs_the_without_windows(self):
        row = verdict_of(series("a", [4] * 6, [2, 4]))
        self.assertEqual(row["verdict"], "stable")
        self.assertIsNone(row["numbers"]["delta"])

    def test_improved_on_a_rise(self):
        row = verdict_of(series("a", [2, 2, 2, 4, 4, 4]))
        self.assertEqual(row["verdict"], "improved")

    def test_a_drop_exactly_at_the_threshold_regresses(self):
        policies = {name: {**POLICY, "objective_drop": 0.25} for name in POLICIES}
        self.assertEqual(verdict_of(series("a", [4, 4, 4, 3, 3, 3]), policies)["verdict"],
                         "regressed")
        self.assertEqual(verdict_of(series("a", [4] * 6, judge=[8, 8, 8, 7, 7, 7]))["verdict"],
                         "regressed")
        self.assertEqual(verdict_of(series("a", [3, 3, 3, 4, 4, 4]), policies)["verdict"],
                         "improved")

    def test_lost_delta_at_exactly_the_minimum_and_zero(self):
        policies = {name: {**POLICY, "lost_delta_min_previous": 0.25} for name in POLICIES}
        row = verdict_of(series("a", [4] * 6, [3, 3, 3, 4, 4, 4]), policies)
        self.assertEqual(row["verdict"], "lost-delta")

    def test_improved_when_the_delta_appears(self):
        policies = {name: {**POLICY, "objective_drop": 0.9} for name in POLICIES}
        row = verdict_of(series("a", [2, 2, 2, 3, 3, 3], [2] * 6), policies)
        self.assertEqual(row["verdict"], "improved")
        self.assertIn("with minus without", row["reason"])

    def test_stable(self):
        row = verdict_of(series("a", [3] * 6, [1] * 6))
        self.assertEqual(row["verdict"], "stable")
        self.assertEqual(row["numbers"]["delta"], {"previous": 0.5, "current": 0.5})

    def test_insufficient_with_one_run_in_a_window(self):
        row = verdict_of(series("a", [4, 2, 2, 2]))
        self.assertEqual(row["verdict"], "insufficient")
        self.assertEqual(len(row["windows"]["previous"]), 1)
        self.assertIsNone(row["numbers"]["objective"])
        self.assertIn("fewer than 2 runs", row["reason"])

    def test_the_noise_guard_suppresses_a_drop_inside_noise(self):
        noisy = verdict_of(series("a", [4, 1, 4, 2, 4, 1]))
        self.assertGreaterEqual(-noisy["numbers"]["objective"]["change"], 0.15)
        self.assertGreater(noisy["numbers"]["objective"]["noise"],
                           -noisy["numbers"]["objective"]["change"])
        self.assertEqual(noisy["verdict"], "stable")
        quiet = verdict_of(series("a", [3, 3, 3, 2, 2, 2]))
        self.assertEqual(quiet["verdict"], "regressed")

    def test_the_judge_noise_guard(self):
        row = verdict_of(series("a", [4] * 6, judge=[9, 5, 9, 8, 3, 9]))
        self.assertEqual(row["verdict"], "stable")

    def test_pooled_noise_is_the_documented_figure(self):
        row = verdict_of(series("a", [4, 1, 4, 2, 4, 1]))
        previous, current = [1.0, 0.25, 1.0], [0.5, 1.0, 0.25]
        squares = sum((v - sum(w) / 3) ** 2 for w in (previous, current) for v in w)
        self.assertAlmostEqual(row["numbers"]["objective"]["noise"], (squares / 4) ** 0.5)

    def test_a_changed_fixture_excludes_the_older_runs(self):
        runs = (series("a", [4, 4, 4], fixture_digest="old")
                + series("a", [1, 1, 1], first=4, fixture_digest="new"))
        row = verdict_of(runs)
        self.assertEqual(row["verdict"], "insufficient")
        self.assertEqual(row["windows"]["previous"], [])
        self.assertEqual(len(row["windows"]["current"]), 3)

    def test_a_model_outside_the_roster_is_ignored(self):
        doc = regression.compute(index_of(series("a", [4, 4, 4, 1, 1, 1], model="other")),
                                 MODELS, POLICIES, AS_OF)
        self.assertEqual(doc["rows"], [])
        self.assertEqual(doc["subjects"], {"skill": {}, "guidance": {}})

    def test_bare_runs_are_never_read(self):
        doc = regression.compute(index_of(bare=series("a", [4, 4, 4, 1, 1, 1])),
                                 MODELS, POLICIES, AS_OF)
        self.assertEqual(doc["rows"], [])

    def test_runs_that_do_not_count_are_left_out(self):
        broken = series("a", [4, 4, 4, 2, 2, 2])
        broken[4]["trials"] = [{"scored": False, "infrastructure": True, "errored": False,
                                "cost_usd": None}]
        row = verdict_of(broken)
        self.assertNotIn(stamp(5), [r["timestamp"] for w in row["windows"].values()
                                    for r in w])
        self.assertEqual([r["timestamp"] for r in row["windows"]["previous"]],
                         [stamp(1), stamp(2)])
        self.assertEqual(row["verdict"], "regressed")

    def test_windows_boundary_and_run_entries(self):
        row = verdict_of(series("a", [4, 4, 4, 2, 2, 2]))
        self.assertEqual(row["boundary"], {"after": stamp(3), "before": stamp(4)})
        entry = row["windows"]["current"][0]
        self.assertEqual(entry, {
            "timestamp": stamp(4), "path": f"results/a/{stamp(4)}",
            "report": gates._link(f"results/a/{stamp(4)}/report.md"),
            "tested_digest": "t1", "cli_versions": ["1.0"], "arm_context_digest": "ctx"})

    def test_only_the_newest_windows_count(self):
        row = verdict_of(series("a", [0, 0, 4, 4, 4, 4, 4, 4]))
        self.assertEqual(row["verdict"], "stable")
        self.assertEqual(row["windows"]["previous"][0]["timestamp"], stamp(3))

    def test_rows_and_json_are_deterministic_and_finite(self):
        runs = (series("b", [4, 4, 4, 2, 2, 2], fixture="y") + series("b", [4] * 6, fixture="x")
                + series("a", [3] * 6, model=OPUS))
        doc = regression.compute(index_of(runs), MODELS, POLICIES, AS_OF)
        self.assertEqual([(r["id"], r["fixture"], r["model"]) for r in doc["rows"]],
                         [("a", None, OPUS), ("b", "x", SONNET), ("b", "y", SONNET)])
        self.assertEqual(doc["subjects"]["skill"], {"a": "stable", "b": "regressed"})
        self.assertEqual(doc["roster_models"], MODELS)
        self.assertEqual(doc["as_of"], AS_OF)
        self.assertEqual(json.dumps(doc, allow_nan=False, sort_keys=True),
                         json.dumps(regression.compute(index_of(list(reversed(runs))), MODELS,
                                                        POLICIES, AS_OF),
                                    allow_nan=False, sort_keys=True))


class GuidanceTests(unittest.TestCase):
    def guidance_runs(self, passed, **kw):
        return ([run("sec", "with", 1 + i, p, pair="in_situ", **kw)
                 for i, p in enumerate(passed)]
                + [run("sec", "with", 1 + i, p, pair="alone", **kw)
                   for i, p in enumerate([4] * 6)])

    def test_rows_carry_subject_and_pair(self):
        doc = regression.compute(index_of(guidance=self.guidance_runs([4, 4, 4, 2, 2, 2])),
                                 MODELS, POLICIES, AS_OF)
        self.assertEqual([(r["subject"], r["id"], r["pair"], r["verdict"])
                          for r in doc["rows"]],
                         [("guidance", "sec", "alone", "stable"),
                          ("guidance", "sec", "in_situ", "regressed")])
        self.assertEqual(doc["subjects"], {"skill": {}, "guidance": {"sec": "regressed"}})
        self.assertEqual(set(gates.GUIDANCE_PAIRS), {"in_situ", "alone"})

    def test_the_guidance_policy_block_governs_guidance_cells(self):
        loose = {"skills": dict(POLICY), "guidance": {**POLICY, "objective_drop": 0.9}}
        runs = series("x", [4, 4, 4, 2, 2, 2])
        self.assertEqual(verdict_of(runs, loose)["verdict"], "regressed")
        as_guidance = [{**r, "pair": "in_situ"} for r in runs]
        self.assertEqual(verdict_of(as_guidance, loose, guidance=True)["verdict"], "stable")

    def test_a_skill_and_a_section_with_one_id_are_two_subjects(self):
        doc = regression.compute(
            index_of(series("same", [4, 4, 4, 2, 2, 2]),
                     [{**r, "pair": "in_situ"} for r in series("same", [4] * 6)]),
            MODELS, POLICIES, AS_OF)
        self.assertEqual(doc["subjects"], {"skill": {"same": "regressed"},
                                           "guidance": {"same": "stable"}})


class SuspectTests(unittest.TestCase):
    def test_every_difference_between_the_windows_is_named(self):
        runs = ([run("a", "with", d, 4, tested="old", cli=("1.0",), context="c1")
                 for d in (1, 2, 3)]
                + [run("a", "with", d, 2, tested="new", cli=("1.1",), context="c2")
                   for d in (4, 5, 6)])
        row = verdict_of(runs)
        self.assertEqual(row["suspects"], ["skill content changed", "CLI version changed",
                                           "arm context changed"])

    def test_a_section_says_section(self):
        runs = ([run("s", "with", d, 4, pair="in_situ", tested="old") for d in (1, 2, 3)]
                + [run("s", "with", d, 2, pair="in_situ", tested="new") for d in (4, 5, 6)])
        self.assertEqual(verdict_of(runs, guidance=True)["suspects"],
                         ["section content changed"])

    def test_no_difference_no_suspects(self):
        self.assertEqual(verdict_of(series("a", [4, 4, 4, 2, 2, 2]))["suspects"], [])


class SubjectVerdictTests(unittest.TestCase):
    def test_precedence(self):
        order = [("regressed", "lost-delta", "improved", "stable", "insufficient"),
                 ("lost-delta", "improved", "stable", "insufficient"),
                 ("improved", "stable", "insufficient"),
                 ("stable", "insufficient"), ("insufficient",)]
        for verdicts in order:
            self.assertEqual(regression.subject_verdict(reversed(verdicts)), verdicts[0])

    def test_through_the_document(self):
        runs = (series("a", [4, 4, 4, 2, 2, 2], fixture="x") + series("a", [4] * 6, fixture="y"))
        doc = regression.compute(index_of(runs), MODELS, POLICIES, AS_OF)
        self.assertEqual(doc["subjects"]["skill"], {"a": "regressed"})


class PolicyTests(unittest.TestCase):
    def text(self, **change):
        blocks = {name: {**POLICY} for name in ("skills", "guidance")}
        for dotted, value in change.items():
            name, key = dotted.split("__")
            if value is KeyError:
                del blocks[name][key]
            else:
                blocks[name][key] = value
        return yaml.safe_dump(blocks)

    def test_the_committed_policy_loads(self):
        self.assertEqual(regression.load_policy(ROOT / "evals" / "regression-policy.yml"),
                         POLICIES)
        self.assertEqual(regression.load_policy(), POLICIES)

    def test_each_key_is_required_and_checked_in_each_block(self):
        bad = {"window_runs": [1, 2.5, True, "3", None],
               "min_window_runs": [1, 4, 2.5, True, None],
               "objective_drop": [0, -0.1, 1.5, True, "x", float("nan")],
               "judge_drop": [0, -1, 10.5, True, "x"],
               "lost_delta_min_previous": [0, -0.1, 1.01, True, "x"]}
        self.assertEqual(set(bad), set(regression.POLICY_KEYS))
        for block in ("skills", "guidance"):
            for key, values in bad.items():
                with self.assertRaises(regression.RegressionPolicyError, msg=f"{block}.{key}"):
                    regression.parse_policy(self.text(**{f"{block}__{key}": KeyError}))
                for value in values:
                    with self.assertRaises(regression.RegressionPolicyError,
                                           msg=f"{block}.{key}={value!r}") as raised:
                        regression.parse_policy(self.text(**{f"{block}__{key}": value}))
                    self.assertIn(key, str(raised.exception))

    def test_the_bounds_are_inclusive_where_stated(self):
        for change in ({"skills__window_runs": 2, "skills__min_window_runs": 2},
                       {"skills__objective_drop": 1}, {"skills__judge_drop": 10}):
            regression.parse_policy(self.text(**change))

    def test_structure_errors(self):
        for text in ("[", "- 1", "skills: {}", yaml.safe_dump({"skills": POLICY}),
                     yaml.safe_dump({"skills": POLICY, "guidance": POLICY, "x": 1}),
                     yaml.safe_dump({"skills": POLICY, "guidance": [1]}),
                     yaml.safe_dump({"skills": POLICY, "guidance": {**POLICY, "extra": 1}})):
            with self.assertRaises(regression.RegressionPolicyError):
                regression.parse_policy(text)

    def test_an_unreadable_file(self):
        with self.assertRaises(regression.RegressionPolicyError):
            regression.load_policy(ROOT / "evals" / "no-such-policy.yml")
        self.assertTrue(issubclass(regression.RegressionPolicyError, ValueError))


# ---------------------------------------------------------------------------
# The issue script.

class FakeGh:
    """Answers the issue listing and records every write. `fail` names a
    write whose first argument pair or title makes it raise."""

    def __init__(self, issues=(), fail=()):
        self.issues = list(issues)
        self.fail = tuple(fail)
        self.writes = []

    def __call__(self, args, stdin=None):
        if args[0] == "api":
            return "".join(json.dumps(i) + "\n" for i in self.issues)
        if any(token in " ".join(args) for token in self.fail):
            raise retire_skill.RetireError(f"gh {args[0]} exited 1")
        self.writes.append((args, stdin))
        return ""


def record(number, body, author=BOT, state="open"):
    return {"number": number, "body": body, "author": author, "state": state}


def fake_git(log=""):
    calls = []

    def git(checkout, args):
        calls.append((Path(checkout), list(args)))
        return log
    git.calls = calls
    return git


class IssueTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.dir = Path(self.tmp.name)
        self.out = self.dir / "regressions" / "latest.json"
        self.index = index_of(
            series("alpha", [4, 4, 4, 2, 2, 2])
            + series("beta", [3] * 6)
            + series("gamma", [4, 2, 2, 2]),
            [{**r, "pair": "in_situ"} for r in series("alpha", [4, 4, 4, 2, 2, 2])])

    def main(self, gh, *extra, git=None, index=None, args=None):
        argv = ["--results-tree", str(self.dir), "--roster", str(ROOT / "evals/roster.yml"),
                "--policy", str(ROOT / "evals/regression-policy.yml"),
                "--as-of", "2026-10-31T00:00:00+00:00", "--out", str(self.out), *extra]
        out, err = io.StringIO(), io.StringIO()
        with mock.patch.object(compute_gates, "build_index",
                               return_value=index or self.index), redirect_stderr(err):
            code = regression_issue.main(args or argv, gh=gh, git=git or fake_git(), out=out)
        return code, out.getvalue(), err.getvalue()

    def kinds(self, gh):
        return [tuple(args[:2]) for args, _ in gh.writes]

    def test_create_when_none_for_both_subjects(self):
        gh = FakeGh()
        code, _out, err = self.main(gh, "--run-url", "https://example.com/run/1")
        self.assertEqual((code, err), (0, ""))
        creates = [(a, s) for a, s in gh.writes if a[:2] == ["issue", "create"]]
        self.assertEqual(len(creates), 2)
        skill, guidance = creates
        self.assertEqual(skill[0][skill[0].index("--title") + 1],
                         f"Regression: alpha no longer helps on {SONNET}")
        self.assertEqual(guidance[0][guidance[0].index("--title") + 1],
                         f'Regression: fleet guidance section "alpha" no longer helps on '
                         f"{SONNET}")
        self.assertIn("<!-- skills-evals:regression:alpha -->\n", skill[1])
        self.assertIn("<!-- skills-evals:regression:guidance:alpha -->\n", guidance[1])
        self.assertNotIn("regression:guidance", skill[1])
        for args, body in creates:
            self.assertEqual(args[args.index("-R") + 1], "Adam-S-Daniel/skills-evals")
            self.assertIn(regression_issue.CLOSING, body)
            self.assertIn("Workflow run: https://example.com/run/1", body)
        self.assertIn("| `in_situ` |", guidance[1])
        self.assertEqual(json.loads(self.out.read_text())["subjects"]["skill"],
                         {"alpha": "regressed", "beta": "stable", "gamma": "insufficient"})

    def test_the_document_is_written_canonically(self):
        self.main(FakeGh())
        text = self.out.read_text()
        self.assertTrue(text.endswith("}\n"))
        self.assertEqual(text, json.dumps(json.loads(text), indent=2, sort_keys=True,
                                          allow_nan=False) + "\n")

    def test_body_figures_and_links(self):
        gh = FakeGh()
        self.main(gh)
        body = gh.writes[0][1]
        self.assertIn(f"| (flat) | `{SONNET}` | regressed | 1.000 → 0.500 | -0.500 | 0.000 | "
                      "n/a | n/a |", body)
        self.assertIn(f"[results/alpha/{stamp(4)}/report.md]", body)
        self.assertIn("Registry not checked out.", body)
        self.assertIn("none of skill content", body)

    def test_update_when_open_and_changed(self):
        gh = FakeGh([record(7, "<!-- skills-evals:regression:alpha -->\nold figures\n")])
        code, _out, _err = self.main(gh)
        self.assertEqual(code, 0)
        edits = [a for a, _ in gh.writes if a[:2] == ["issue", "edit"]]
        self.assertEqual(len(edits), 1)
        self.assertEqual(edits[0][2], "7")
        self.assertIn("--title", edits[0])
        self.assertEqual(self.kinds(gh).count(("issue", "create")), 1)  # the section's

    def test_no_op_when_open_and_unchanged(self):
        first = FakeGh()
        self.main(first, "--run-url", "https://example.com/run/1")
        bodies = [s for _a, s in first.writes]
        gh = FakeGh([record(7, bodies[0]), record(8, bodies[1])])
        code, _out, _err = self.main(gh, "--run-url", "https://example.com/run/2")
        self.assertEqual((code, gh.writes), (0, []))

    def test_close_with_a_comment_when_recovered(self):
        index = index_of(series("beta", [3] * 6))
        gh = FakeGh([record(9, "<!-- skills-evals:regression:beta -->\nx\n")])
        code, _out, _err = self.main(gh, index=index)
        self.assertEqual(code, 0)
        self.assertEqual([a[:2] for a, _ in gh.writes], [["issue", "comment"],
                                                         ["issue", "close"]])
        comment, close = gh.writes
        self.assertEqual(comment[0][2], "9")
        self.assertIn("stable", comment[1])
        self.assertIn("20261031T000000Z", comment[1])
        self.assertEqual(close[0][-2:], ["--reason", "completed"])

    def test_improved_closes_too(self):
        index = index_of(series("beta", [2, 2, 2, 4, 4, 4]))
        gh = FakeGh([record(9, "<!-- skills-evals:regression:beta -->\n")])
        self.main(gh, index=index)
        self.assertEqual([a[1] for a, _ in gh.writes], ["comment", "close"])

    def test_no_op_on_insufficient_even_with_an_open_issue(self):
        index = index_of(series("gamma", [4, 2, 2, 2]))
        gh = FakeGh([record(9, "<!-- skills-evals:regression:gamma -->\n")])
        self.main(gh, index=index)
        self.assertEqual(gh.writes, [])

    def test_no_op_when_already_closed_and_stable(self):
        index = index_of(series("beta", [3] * 6))
        gh = FakeGh([record(9, "<!-- skills-evals:regression:beta -->\n", state="closed")])
        self.main(gh, index=index)
        self.assertEqual(gh.writes, [])

    def test_a_closed_issue_does_not_stop_a_new_one(self):
        gh = FakeGh([record(5, "<!-- skills-evals:regression:alpha -->\n", state="closed")])
        self.main(gh)
        self.assertEqual(self.kinds(gh).count(("issue", "create")), 2)

    def test_dry_run_writes_nothing_and_prints_the_plan(self):
        gh = FakeGh()
        code, out, _err = self.main(gh, "--dry-run")
        self.assertEqual((code, gh.writes), (0, []))
        plan = json.loads(out)
        self.assertTrue(plan["dry_run"])
        actions = {(a["subject"], a["id"]): a["action"] for a in plan["actions"]}
        self.assertEqual(actions, {("skill", "alpha"): "create-issue",
                                   ("skill", "beta"): "none",
                                   ("skill", "gamma"): "none",
                                   ("guidance", "alpha"): "create-issue"})
        self.assertEqual(plan["actions"][0]["would_run"][0][:3], ["gh", "issue", "create"])
        self.assertTrue(self.out.is_file())

    def test_markers_never_collide_across_subjects(self):
        both = [record(1, "<!-- skills-evals:regression:alpha -->\n"),
                record(2, "<!-- skills-evals:regression:guidance:alpha -->\n")]
        issues = [dict(i, state="open") for i in both]
        skill = regression_issue.open_issue(issues, "skill", "alpha")
        guidance = regression_issue.open_issue(issues, "guidance", "alpha")
        self.assertEqual((skill["number"], guidance["number"]), (1, 2))
        only_guidance = [issues[1]]
        self.assertIsNone(regression_issue.open_issue(only_guidance, "skill", "alpha"))
        self.assertIsNone(regression_issue.open_issue(issues, "skill", "alph"))
        quoted = [{"number": 3, "state": "open",
                   "body": "see <!-- skills-evals:regression:alpha --> in prose\n"}]
        self.assertIsNone(regression_issue.open_issue(quoted, "skill", "alpha"))

    def test_an_issue_by_another_author_is_ignored(self):
        gh = FakeGh([record(3, "<!-- skills-evals:regression:alpha -->\n",
                            author="someone-else")])
        self.main(gh)
        self.assertEqual(self.kinds(gh).count(("issue", "create")), 2)
        self.assertNotIn(("issue", "edit"), self.kinds(gh))

    def test_the_lowest_open_issue_is_the_one_acted_on(self):
        gh = FakeGh([record(12, "<!-- skills-evals:regression:alpha -->\nb\n"),
                     record(4, "<!-- skills-evals:regression:alpha -->\na\n")])
        self.main(gh)
        edits = [a for a, _ in gh.writes if a[:2] == ["issue", "edit"]]
        self.assertEqual([e[2] for e in edits], ["4"])

    def test_a_gh_failure_on_one_subject_does_not_stop_the_others(self):
        index = index_of(series("alpha", [4, 4, 4, 2, 2, 2]) + series("beta", [3] * 6))
        gh = FakeGh([record(9, "<!-- skills-evals:regression:beta -->\n")],
                    fail=("Regression: alpha",))
        code, _out, err = self.main(gh, index=index)
        self.assertEqual(code, 1)
        self.assertEqual([a[1] for a, _ in gh.writes], ["comment", "close"])
        self.assertIn("skill alpha", err)
        self.assertNotIn("Regression:", err)

    def test_a_failed_listing_is_exit_one_and_writes_nothing(self):
        def broken(args, stdin=None):
            raise retire_skill.RetireError("gh api exited 1")
        code, _out, _err = self.main(broken)
        self.assertEqual(code, 1)

    def test_bad_input_is_exit_two(self):
        base = ["--results-tree", str(self.dir), "--roster", str(ROOT / "evals/roster.yml"),
                "--policy", str(ROOT / "evals/regression-policy.yml"),
                "--as-of", "20261031T000000Z", "--out", str(self.out)]

        def swap(flag, value):
            argv = list(base)
            argv[argv.index(flag) + 1] = value
            return argv
        bad_policy = self.dir / "policy.yml"
        bad_policy.write_text("skills: {}\n")
        empty_roster = self.dir / "roster.yml"
        empty_roster.write_text("schema: 1\narms: []\n")
        for argv in (swap("--policy", str(bad_policy)), swap("--as-of", "yesterday"),
                     swap("--as-of", "2026-10-31T00:00:00"),
                     swap("--roster", str(empty_roster)),
                     swap("--roster", str(self.dir / "missing.yml")),
                     swap("--policy", str(self.dir / "missing.yml"))):
            gh = FakeGh()
            code, _out, _err = self.main(gh, args=argv)
            self.assertEqual((code, gh.writes), (2, []), argv)


def registry_entry(repo: Path) -> dict:
    """A resolved registry entry, shaped as compute_gates.flag_registries
    returns it."""
    return {"name": "adam-agentskills", "path": repo, "layout": "plugins/*/skills/*/SKILL.md",
            "url": "https://github.com/Adam-S-Daniel/adam-agentskills",
            "source": "--registry flag"}


class CommitRangeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.dir = Path(self.tmp.name)

    def commit(self, repo, rel, date, text):
        path = repo / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
        env = {**os.environ, "GIT_AUTHOR_DATE": date, "GIT_COMMITTER_DATE": date}
        for args in (["add", "-A"], ["commit", "-q", "-m", "change"]):
            subprocess.run(["git", "-C", str(repo), "-c", "user.name=t",
                            "-c", "user.email=t@example.com", *args],
                           check=True, capture_output=True, env=env)
        return subprocess.run(["git", "-C", str(repo), "rev-parse", "HEAD"], check=True,
                              capture_output=True, text=True).stdout.strip()

    def repo(self, name):
        repo = self.dir / name
        repo.mkdir()
        subprocess.run(["git", "-C", str(repo), "init", "-q"], check=True,
                       capture_output=True)
        return repo

    def rows(self, subject="skill", ident="alpha"):
        runs = series(ident, [4, 4, 4, 2, 2, 2])
        if subject == "guidance":
            runs = [{**r, "pair": "in_situ"} for r in runs]
        doc = regression.compute(index_of(*( [[], runs] if subject == "guidance"
                                             else [runs])), MODELS, POLICIES, AS_OF)
        return [r for r in doc["rows"] if r["verdict"] == "regressed"]

    def real_git(self, checkout, args):
        return regression_issue.default_git(checkout, args)

    def test_a_skill_lists_the_commits_between_the_windows(self):
        repo = self.repo("agentskills")
        path = "plugins/p/skills/alpha/SKILL.md"
        self.commit(repo, path, "2026-10-01T00:00:00Z", "one")
        inside = self.commit(repo, path, "2026-10-03T12:00:00Z", "two")
        self.commit(repo, path, "2026-10-20T00:00:00Z", "three")
        self.commit(repo, "plugins/p/skills/other/SKILL.md", "2026-10-03T13:00:00Z", "x")
        entry = registry_entry(repo)
        lines = regression_issue.commit_lines(
            "skill", "alpha", self.rows(), {"adam-agentskills": entry}, None, self.real_git)
        self.assertEqual(lines, [
            "- Commits to `plugins/p/skills/alpha` in Adam-S-Daniel/adam-agentskills from "
            "2026-10-03T00:00:00Z to 2026-10-04T00:00:00Z:",
            f"  - [`{inside[:7]}`](https://github.com/Adam-S-Daniel/adam-agentskills/"
            f"commit/{inside})"])

    def test_a_section_lists_the_guidance_commits(self):
        repo = self.repo("guidance")
        self.commit(repo, "agents-md/base.md", "2026-10-01T00:00:00Z", "one")
        inside = self.commit(repo, "agents-md/sections/x.md", "2026-10-03T12:00:00Z", "two")
        self.commit(repo, "README.md", "2026-10-03T13:00:00Z", "unrelated")
        lines = regression_issue.commit_lines("guidance", "alpha", self.rows("guidance"),
                                              {}, repo, self.real_git)
        self.assertEqual(len(lines), 2)
        self.assertIn(f"[`{inside[:7]}`](https://github.com/Adam-S-Daniel/_agent-guidance/"
                      f"commit/{inside})", lines[1])
        self.assertIn("agents-md/base.md agents-md/sections", lines[0])

    def test_the_git_call_is_exact(self):
        repo = self.repo("agentskills")
        self.commit(repo, "plugins/p/skills/alpha/SKILL.md", "2026-10-03T12:00:00Z", "x")
        git = fake_git("")
        lines = regression_issue.commit_lines(
            "skill", "alpha", self.rows(),
            {"adam-agentskills": registry_entry(repo)},
            None, git)
        self.assertEqual(git.calls, [(repo, [
            "log", "--format=%H", "--after=2026-10-03T00:00:00Z",
            "--before=2026-10-04T00:00:00Z", "--", "plugins/p/skills/alpha"])])
        self.assertTrue(lines[0].endswith("none."))

    def test_git_failure_and_missing_checkouts_never_crash(self):
        repo = self.repo("agentskills")
        self.commit(repo, "plugins/p/skills/alpha/SKILL.md", "2026-10-03T12:00:00Z", "x")

        def failing(checkout, args):
            raise retire_skill.RetireError("git log exited 128")
        registries = {"adam-agentskills": registry_entry(repo)}
        self.assertEqual(regression_issue.commit_lines("skill", "alpha", self.rows(),
                                                       registries, None, failing),
                         ["- Commit range unavailable."])
        self.assertEqual(regression_issue.commit_lines("skill", "alpha", self.rows(), {},
                                                       None, failing),
                         ["- Registry not checked out."])
        self.assertEqual(regression_issue.commit_lines("guidance", "alpha",
                                                       self.rows("guidance"), {}, None,
                                                       failing),
                         ["- Registry not checked out."])
        self.assertEqual(regression_issue.commit_lines("guidance", "alpha",
                                                       self.rows("guidance"), {}, repo,
                                                       failing),
                         ["- Commit range unavailable."])

    def test_an_unknown_registry_name_is_not_linked(self):
        repo = self.repo("agentskills")
        self.commit(repo, "plugins/p/skills/alpha/SKILL.md", "2026-10-03T12:00:00Z", "x")
        entry = registry_entry(repo)
        self.assertEqual(regression_issue.commit_lines(
            "skill", "alpha", self.rows(), {"adam-agentskills-private": entry}, None,
            fake_git()), ["- Registry not checked out."])

    def test_main_passes_the_registry_and_guidance_flags_through(self):
        skills = self.repo("agentskills")
        sha = self.commit(skills, "plugins/p/skills/alpha/SKILL.md",
                          "2026-10-03T12:00:00Z", "two")
        guidance = self.repo("guidance")
        gsha = self.commit(guidance, "agents-md/base.md", "2026-10-03T12:00:00Z", "g")
        index = index_of(series("alpha", [4, 4, 4, 2, 2, 2]),
                         [{**r, "pair": "in_situ"} for r in series("alpha", [4, 4, 4, 2, 2, 2])])
        gh = FakeGh()
        argv = ["--results-tree", str(self.dir), "--roster", str(ROOT / "evals/roster.yml"),
                "--policy", str(ROOT / "evals/regression-policy.yml"),
                "--as-of", AS_OF, "--out", str(self.dir / "out.json"),
                "--registry", f"adam-agentskills={skills}", "--guidance", str(guidance)]
        with mock.patch.object(compute_gates, "build_index", return_value=index):
            code = regression_issue.main(argv, gh=gh, out=io.StringIO())
        self.assertEqual(code, 0)
        bodies = [stdin for _args, stdin in gh.writes]
        self.assertIn(f"adam-agentskills/commit/{sha}", bodies[0])
        self.assertIn(f"_agent-guidance/commit/{gsha}", bodies[1])

    def test_the_timestamp_conversion(self):
        self.assertEqual(regression_issue.iso("20261005T010203Z"), "2026-10-05T01:02:03Z")
        with self.assertRaises(ValueError):
            regression_issue.iso("2026-10-05")


class WorkflowTests(unittest.TestCase):
    """The scheduled wiring, read with a YAML parser, never a line scan."""

    def setUp(self):
        self.doc = yaml.safe_load((ROOT / ".github/workflows/skill-coverage.yml").read_text())
        self.job = self.doc["jobs"]["regression"]
        self.step = next(s for s in self.job["steps"]
                         if "scripts/regression_issue.py" in s.get("run", ""))

    def test_permissions_are_exactly_read_and_issues_write(self):
        self.assertEqual(self.job["permissions"], {"contents": "read", "issues": "write"})
        self.assertEqual(self.doc["permissions"], {})

    def test_runs_from_main_on_schedule_and_dispatch(self):
        self.assertEqual(self.job["if"], "github.ref == 'refs/heads/main'")
        self.assertNotIn("needs", self.job)
        self.assertEqual(set(self.doc[True]), {"schedule", "workflow_dispatch"})

    def test_no_interpolation_in_run_and_every_action_is_locked(self):
        for step in self.job["steps"]:
            if "run" in step:
                self.assertNotIn("${{", step["run"])
            if "uses" in step:
                self.assertIsNone(lock_problem(step["uses"], "skill-coverage.yml"))
                if step["uses"].startswith("actions/checkout@"):
                    self.assertIs(step["with"]["persist-credentials"], False)

    def test_dry_run_is_gated_on_the_event_and_the_input(self):
        self.assertEqual(self.step["env"], {"GH_TOKEN": "${{ github.token }}",
                                            "DRY_RUN_INPUT": "${{ inputs.dry_run }}"})
        run = self.step["run"]
        self.assertTrue(run.startswith("set -euo pipefail\n"))
        self.assertIn("dry=(--dry-run)", run)
        self.assertIn('[ "$GITHUB_EVENT_NAME" = "schedule" ] || '
                      '[ "$DRY_RUN_INPUT" = "false" ]', run)
        self.assertIn("dry=()", run)
        self.assertIn('"${dry[@]}"', run)
        for flag in ("--registry", "--guidance", "--run-url",
                     '--out "$RUNNER_TEMP/regressions/latest.json"'):
            self.assertIn(flag, run)

    def test_checkouts_and_the_artifact(self):
        steps = self.job["steps"]
        histories = {s["with"]["repository"]: s["with"].get("fetch-depth")
                     for s in steps if s.get("with", {}).get("repository")}
        self.assertEqual(histories, {"Adam-S-Daniel/adam-agentskills": 0,
                                     "Adam-S-Daniel/_agent-guidance": 0})
        self.assertTrue(any(s.get("with", {}).get("ref") == "persistent/eval-results"
                            for s in steps))
        upload = steps[-1]
        self.assertTrue(upload["uses"].startswith("actions/upload-artifact@"))
        self.assertEqual(upload["with"]["name"], "regressions")


class PublishWorkflowTests(unittest.TestCase):
    """The regression-publish job, read with a YAML parser."""

    def setUp(self):
        self.doc = yaml.safe_load((ROOT / ".github/workflows/skill-coverage.yml").read_text())
        self.job = self.doc["jobs"]["regression-publish"]
        self.lock = yaml.safe_load((ROOT / ".github/workflows/actions.lock").read_text())

    def test_permissions_needs_and_condition(self):
        self.assertEqual(self.job["permissions"], {"contents": "write"})
        self.assertEqual(self.job["needs"], "regression")
        condition = self.job["if"]
        self.assertIn("github.event_name == 'schedule'", condition)
        self.assertIn("github.ref == 'refs/heads/main'", condition)
        self.assertIn("needs.regression.result == 'success'", condition)
        self.assertNotIn("concurrency", self.job)
        self.assertEqual(self.job["timeout-minutes"], 10)

    def test_no_interpolation_and_every_action_is_locked(self):
        locked = set(self.lock["workflows"][".github/workflows/skill-coverage.yml"])
        for step in self.job["steps"]:
            if "run" in step:
                self.assertNotIn("${{", step["run"])
            if "uses" in step:
                self.assertIn(step["uses"], locked)
                self.assertIsNone(lock_problem(step["uses"], "skill-coverage.yml"))
                if step["uses"].startswith("actions/checkout@"):
                    self.assertIs(step["with"]["persist-credentials"], False)

    def test_writes_only_the_one_path(self):
        script = next(s["run"] for s in self.job["steps"]
                      if "git add" in s.get("run", ""))
        adds = [line.strip() for line in script.splitlines() if "git add" in line]
        self.assertEqual(adds, ["git add -f regressions/latest.json"])
        self.assertIn("persistent/eval-results", script)
        self.assertIn("for attempt in 1 2 3", script)


if __name__ == "__main__":
    unittest.main()
