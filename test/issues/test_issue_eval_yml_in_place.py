#!/usr/bin/env python3
"""eval.yml refuses in-place fixtures before any credential (skills-evals#587).

An in-place fixture (a top-level `context:` mapping in fixture.yaml, ADR
0012) needs the hosted container `delivery.require_hosted` checks for, and
eval.yml's runner is never one. So the `plan` job refuses every such fixture
(plan_scheduled_evals.declares_context, the routine's rule) and lists it,
with the reason, in the step summary; it outputs `count`, the legs left, and
`count == '0'` skips every later job, so nothing mints a credential and the
run still ends successfully. There is no fallback to isolation. Pinned here,
from the parsed workflow and the planner itself:

  * the planner keeps only isolation fixtures (with their planned slots) and
    lists each refused one with the reason; with none refused the matrix is
    unchanged;
  * evaluating the parsed `if:` gates over the job graph, a run whose plan
    left nothing skips every credential-minting job, while `roster_only`
    still refreshes the roster;
  * each eval leg refuses an in-place fixture again, before its own mint,
    and the run step passes `--pairing isolation` only;
  * the context repositories ADR 0012 names stay checked out in full, for
    when this runner can host in-place delivery;
  * bubblewrap and socat are provided for the arm sandbox before the token
    exchange.

Nothing here sleeps, touches the network or calls a model.
"""

from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

import yaml

TEST_DIR = Path(__file__).resolve().parent.parent
REPO_ROOT = TEST_DIR.parent
EVAL_WORKFLOW = REPO_ROOT / ".github" / "workflows" / "eval.yml"
RUN_STEP = "Run the eval (both arms, judge)"
SELECT_STEP = "Select and validate the fixture to run"
SELF = "skills-evals"


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


planner = _load("planner_587", REPO_ROOT / "scripts" / "plan_scheduled_evals.py")
# The GitHub Actions expression evaluator the job-graph gate tests already use,
# so the gates below are evaluated as the PARSED `if:` strings.
_Expr = _load("merged_roster_587",
              TEST_DIR / "issues" / "test_issue_eval_on_merged_roster.py")._Expr


def workflow():
    # PyYAML reads the `on:` key as True; only `jobs` is used here.
    return yaml.safe_load(EVAL_WORKFLOW.read_text(encoding="utf-8"))


def eval_steps():
    return workflow()["jobs"]["eval"]["steps"]


def step_named(name):
    steps = [s for s in eval_steps() if s.get("name") == name]
    assert len(steps) == 1, name
    return steps[0]


def context_repositories():
    names = set()
    for path in sorted((REPO_ROOT / "evals").rglob("fixture.yaml")):
        document = yaml.safe_load(path.read_text(encoding="utf-8"))
        context = document.get("context") if isinstance(document, dict) else None
        if isinstance(context, dict) and context.get("repository"):
            names.add(str(context["repository"]).rsplit("/", 1)[-1])
    return names


def committed_split():
    committed = planner.committed_fixtures(REPO_ROOT)
    in_place = [f for f in committed if planner.declares_context(REPO_ROOT / f)]
    isolation = [f for f in committed if f not in in_place]
    return in_place, isolation


def run_planner(fixtures, tmp):
    """Run the planner's CLI as the plan job does, on a dispatch event."""
    tmp = Path(tmp)
    event = tmp / "event.json"
    event.write_text(json.dumps({"inputs": {"fixture": " ".join(fixtures)}}))
    output, summary = tmp / "output", tmp / "summary"
    env = dict(os.environ, GITHUB_EVENT_NAME="workflow_dispatch",
               GITHUB_EVENT_PATH=str(event), GITHUB_OUTPUT=str(output),
               GITHUB_STEP_SUMMARY=str(summary))
    result = subprocess.run(["python3", "scripts/plan_scheduled_evals.py"], cwd=REPO_ROOT,
                            env=env, capture_output=True, text=True)
    outputs = {}
    if output.is_file():
        for line in output.read_text().splitlines():
            key, _, value = line.partition("=")
            outputs[key] = value
    return result, outputs, summary.read_text() if summary.is_file() else ""


class PlannerRefusesInPlaceTests(unittest.TestCase):
    def setUp(self):
        self.in_place, self.isolation = committed_split()
        self.assertGreaterEqual(len(self.in_place), 2)
        self.assertGreaterEqual(len(self.isolation), 2)

    def test_a_mix_passes_on_only_the_isolation_fixtures(self):
        fixtures = [self.in_place[0], self.isolation[0], self.in_place[1], self.isolation[1]]
        with tempfile.TemporaryDirectory() as tmp:
            result, outputs, summary = run_planner(fixtures, tmp)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        # Kept legs keep their planned slot; refused ones simply leave.
        self.assertEqual(json.loads(outputs["matrix"]), {"include": [
            {"fixture": self.isolation[0], "eval_key": self.isolation[0][6:], "slot": 1},
            {"fixture": self.isolation[1], "eval_key": self.isolation[1][6:], "slot": 3}]})
        self.assertEqual(outputs["count"], "2")
        for fixture in self.in_place[:2]:
            self.assertIn(f"- `{fixture}`: {planner.IN_PLACE_REFUSAL}\n", summary)
        for fixture in self.isolation[:2]:
            self.assertNotIn(fixture, summary)
        self.assertIn("2 fixture(s) left to run.", summary)
        self.assertIn("::notice::2 in-place fixture(s) refused, 2 left", result.stdout)

    def test_all_in_place_leaves_an_empty_set_and_says_why(self):
        with tempfile.TemporaryDirectory() as tmp:
            result, outputs, summary = run_planner(self.in_place[:3], tmp)
        # Success, not a failure: the summary is the explanation.
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(json.loads(outputs["matrix"]), {"include": []})
        self.assertEqual(outputs["count"], "0")
        self.assertEqual(summary.count(planner.IN_PLACE_REFUSAL), 3)
        self.assertIn("No fixture is left to run", summary)
        self.assertNotIn("::error::", result.stdout)

    def test_the_default_dispatch_is_refused_when_it_is_in_place(self):
        # The default fixture is itself an in-place pair today.
        with tempfile.TemporaryDirectory() as tmp:
            result, outputs, _ = run_planner([], tmp)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        want = "0" if planner.DEFAULT_FIXTURE in self.in_place else "1"
        self.assertEqual(outputs["count"], want)

    def test_no_in_place_fixture_leaves_the_plan_unchanged(self):
        fixtures = self.isolation[:3]
        planned = planner.plan(REPO_ROOT, "workflow_dispatch",
                               {"inputs": {"fixture": " ".join(fixtures)}})
        self.assertEqual(planner.refuse_in_place(REPO_ROOT, planned), (planned, []))
        with tempfile.TemporaryDirectory() as tmp:
            result, outputs, summary = run_planner(fixtures, tmp)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(json.loads(outputs["matrix"]), planned)
        self.assertEqual(outputs["count"], "3")
        self.assertEqual(summary, "")
        self.assertNotIn("::notice::", result.stdout)

    def test_the_reason_names_the_routine_and_the_issue(self):
        self.assertEqual(planner.IN_PLACE_REFUSAL,
                         "in-place pair: runs only in the cloud routine, which hosts "
                         "in-place delivery; eval.yml cannot (skills-evals#587)")

    def test_an_invalid_selection_still_fails_without_a_count(self):
        with tempfile.TemporaryDirectory() as tmp:
            result, outputs, _ = run_planner([self.isolation[0], "evals/nope"], tmp)
        self.assertEqual(result.returncode, 1)
        self.assertNotIn("count", outputs)


def credential_jobs(jobs):
    """Jobs that mint a credential: a WIF `id-token: write`, or a GitHub App
    installation token. Derived from the parsed workflow, never listed."""
    minting = set()
    for name, job in jobs.items():
        if (job.get("permissions") or {}).get("id-token") == "write":
            minting.add(name)
        for step in job.get("steps", []):
            if str(step.get("uses", "")).startswith("actions/create-github-app-token@"):
                minting.add(name)
    return minting


def simulate(jobs, *, count, roster_only=False, plan_result="success",
             ref="refs/heads/main"):
    """Which jobs run, evaluating each parsed `if:` in dependency order.
    Every job but `plan` gates on `!cancelled()`, so its `if:` alone decides;
    a job that runs is taken to succeed, and `roster-wait` to confirm clear."""
    results = {"plan": plan_result}
    outputs = {"plan": {"count": count if plan_result == "success" else ""}}
    pending = [name for name in jobs if name != "plan"]
    while pending:
        for name in pending:
            needs = jobs[name].get("needs") or []
            needs = [needs] if isinstance(needs, str) else needs
            if all(need in results for need in needs):
                break
        else:
            raise AssertionError("cycle in needs")
        pending.remove(name)
        ctx = {"functions": {"cancelled": lambda: False},
               "inputs.roster_only": roster_only, "github.ref": ref}
        for need in needs:
            ctx[f"needs.{need}.result"] = results[need]
            for key, value in outputs.get(need, {}).items():
                ctx[f"needs.{need}.outputs.{key}"] = value
        ran = bool(_Expr(jobs[name]["if"], ctx).value())
        results[name] = "success" if ran else "skipped"
        if name == "roster-wait":
            outputs[name] = {"cleared": "true" if ran else ""}
    return {name for name, result in results.items() if result == "success"} - {"plan"}


class WorkflowGatesTests(unittest.TestCase):
    def setUp(self):
        self.jobs = workflow()["jobs"]
        self.minting = credential_jobs(self.jobs)

    def test_the_minting_jobs_are_found(self):
        # A negative control for the derivation: these mint today.
        self.assertLessEqual({"roster", "eval", "roster-pr"}, self.minting)

    def test_the_plan_job_holds_no_credential_and_outputs_count(self):
        plan = self.jobs["plan"]
        self.assertEqual(plan["permissions"], {"contents": "read"})
        self.assertNotIn("plan", self.minting)
        self.assertNotIn("secrets.", json.dumps(plan))
        self.assertEqual(plan["outputs"]["count"], "${{ steps.plan.outputs.count }}")
        step = next(s for s in plan["steps"] if s.get("id") == "plan")
        self.assertEqual(step["run"], "python3 scripts/plan_scheduled_evals.py")
        self.assertNotIn("${{", step["run"])

    def test_every_minting_job_runs_after_the_plan(self):
        def ancestors(name):
            seen, stack = set(), [name]
            while stack:
                needs = self.jobs[stack.pop()].get("needs") or []
                for need in [needs] if isinstance(needs, str) else needs:
                    if need not in seen:
                        seen.add(need)
                        stack.append(need)
            return seen
        for name in sorted(self.minting):
            with self.subTest(job=name):
                self.assertIn("plan", ancestors(name))

    def test_nothing_left_means_no_job_runs_at_all(self):
        for ref in ("refs/heads/main", "refs/heads/other"):
            with self.subTest(ref=ref):
                self.assertEqual(simulate(self.jobs, count="0", ref=ref), set())

    def test_a_failed_plan_mints_nothing_either(self):
        self.assertEqual(simulate(self.jobs, count="", plan_result="failure"), set())

    def test_roster_only_still_refreshes_the_roster_with_nothing_left(self):
        for plan_result in ("success", "failure"):
            with self.subTest(plan_result=plan_result):
                ran = simulate(self.jobs, count="0", roster_only=True, plan_result=plan_result)
                self.assertEqual(ran, {"roster", "disarm", "roster-pr"})

    def test_a_fixture_left_runs_the_whole_graph_as_before(self):
        self.assertEqual(simulate(self.jobs, count="2"), set(self.jobs) - {"plan"})
        # Off `main`: no roster PR jobs, but the eval and publish still run.
        self.assertEqual(simulate(self.jobs, count="1", ref="refs/heads/other"),
                         {"roster", "eval", "publish"})

    def test_the_eval_gate_needs_count_itself(self):
        # With `roster-wait` skipped, its clause passes, so the eval's own
        # `count` clause is what keeps an empty matrix from running.
        ctx = {"functions": {"cancelled": lambda: False}, "inputs.roster_only": False,
               "needs.plan.result": "success", "needs.plan.outputs.count": "0",
               "needs.roster-wait.result": "skipped",
               "needs.roster-wait.outputs.cleared": ""}
        self.assertFalse(_Expr(self.jobs["eval"]["if"], ctx).value())
        ctx["needs.plan.outputs.count"] = "1"
        self.assertTrue(_Expr(self.jobs["eval"]["if"], ctx).value())


class EvalWorkflowInPlaceTests(unittest.TestCase):
    def test_some_fixture_declares_context(self):
        self.assertTrue(context_repositories())

    def test_every_context_repository_is_checked_out_in_full(self):
        checkouts = {}
        for step in eval_steps():
            if str(step.get("uses", "")).startswith("actions/checkout@"):
                with_ = step.get("with", {})
                name = str(with_.get("repository", SELF)).rsplit("/", 1)[-1]
                checkouts[name] = with_
        for name in sorted(context_repositories()):
            with self.subTest(repository=name):
                self.assertIn(name, checkouts)
                with_ = checkouts[name]
                self.assertEqual(with_.get("path"), name)
                self.assertEqual(with_.get("fetch-depth"), 0)
                self.assertIs(with_.get("persist-credentials"), False)

    def test_run_step_passes_isolation_only(self):
        script = step_named(RUN_STEP)["run"]
        self.assertIn("--pairing isolation", script)
        self.assertEqual(script.count("--pairing"), 1)
        self.assertNotIn("in_place", script)
        self.assertNotIn("declares_context", script)

    def _select(self, fixture, tmp):
        script = step_named(SELECT_STEP)["run"]
        env = dict(os.environ, MATRIX_FIXTURE=fixture, MATRIX_KEY=fixture[6:],
                   MATRIX_SLOT="0", GITHUB_OUTPUT=str(Path(tmp) / "out"), RUNNER_TEMP=tmp)
        return subprocess.run(["bash", "-c", script], cwd=REPO_ROOT, env=env,
                              capture_output=True, text=True)

    def test_each_leg_refuses_an_in_place_fixture_before_its_mint(self):
        in_place, isolation = committed_split()
        names = [s.get("name") for s in eval_steps()]
        mint = next(i for i, n in enumerate(names) if n and n.startswith("Mint OIDC"))
        self.assertLess(names.index(SELECT_STEP), mint)
        with tempfile.TemporaryDirectory() as tmp:
            result = self._select(in_place[0], tmp)
            self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
            self.assertIn(planner.IN_PLACE_REFUSAL, result.stdout)
            self.assertFalse((Path(tmp) / "eval-key").exists())
        with tempfile.TemporaryDirectory() as tmp:
            result = self._select(isolation[0], tmp)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertEqual((Path(tmp) / "eval-key").read_text(), isolation[0][6:])


class EvalWorkflowArmSandboxTests(unittest.TestCase):
    """Arms require the CLI sandbox; without bwrap and socat every arm ends
    in sandbox_unavailable (run 41493765048)."""

    def test_sandbox_tools_are_provided_before_any_credential(self):
        steps = eval_steps()
        names = [step.get("name") for step in steps]
        provision = names.index("Provide bubblewrap and socat for the arm sandbox")
        mint = next(i for i, name in enumerate(names)
                    if name and name.startswith("Mint OIDC token"))
        self.assertLess(provision, mint)
        self.assertLess(provision, names.index(RUN_STEP))
        script = steps[provision]["run"].split()
        for token in ("bubblewrap", "socat", "apparmor_parser", "--unshare-net", "--unshare-pid"):
            self.assertIn(token, script)
        self.assertNotIn("${{", steps[provision]["run"])


if __name__ == "__main__":
    unittest.main()
