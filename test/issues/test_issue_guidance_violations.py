"""Passive real-work fleet counters: differential artifacts and bounded traces."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "harness"))

import cli_json  # noqa: E402
import guidance_violations as counters  # noqa: E402
import run_eval  # noqa: E402

SHA = "a" * 40
OTHER_SHA = "b" * 40
WORKFLOW = ".github/workflows/ci.yml"


def trace(*commands):
    events = []
    for index, item in enumerate(commands):
        command, failed = item if isinstance(item, tuple) else (item, False)
        ident = f"tool-{index}"
        events.extend([
            {"call": 0, "kind": "tool_use", "name": "Bash", "id": ident,
             "input": command, "input_chars": len(command), "subagent": False},
            {"call": 0, "kind": "tool_result", "id": ident, "is_error": failed,
             "output": "", "output_chars": 0, "subagent": False}])
    return {"schema_version": 1, "events": events, "omitted_events": 0}


def workflow(steps):
    return "jobs:\n  test:\n    steps:\n" + steps


class GuidanceViolationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.workspace = Path(self.temp.name) / "ws"
        self.workspace.mkdir()

    def write(self, value, path=WORKFLOW):
        target = self.workspace / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(value, encoding="utf-8")
        return target

    def measure(self, before=None, evidence=None):
        return counters.measure(before or counters.snapshot(self.workspace),
                                self.workspace, evidence if evidence is not None else trace())

    def test_new_yaml_violations_exclude_inherited_occurrences(self):
        old = workflow("      - uses: actions/checkout@v4\n      - run: echo '${{ inputs.old }}'\n")
        self.write(old)
        before = counters.snapshot(self.workspace)
        self.write(old + "      - uses: actions/setup-node@main\n      - run: echo '${{ github.event.issue.title }}'\n")
        rules = self.measure(before)["rules"]
        self.assertEqual(rules["unpinned_actions"]["count"], 1)
        self.assertEqual(rules["event_input_in_run"]["count"], 1)
        self.assertNotIn("issue.title", json.dumps(rules))

    def test_yaml_carveouts_contexts_and_harmless_run_edits(self):
        self.write(workflow("      - run: echo '${{ inputs.old }}'\n"))
        before = counters.snapshot(self.workspace)
        self.write(workflow(
            "      - run: echo '${{ inputs.old }}'; echo harmless\n"
            f"      - uses: actions/checkout@{SHA}\n"
            "      - uses: ./local/action\n      - uses: docker://image:tag\n"
            "      - uses: Adam-S-Daniel/cms-platform/.github/actions/demo@v0.1.88\n"
            "      - env: {uses: decoy@main, run: '${{ inputs.decoy }}'}\n")
            + "runs: {using: composite, steps: [{uses: decoy@main}]}\n")
        rules = self.measure(before)["rules"]
        self.assertEqual(rules["unpinned_actions"]["count"], 0)
        self.assertEqual(rules["event_input_in_run"]["count"], 0)

    def test_composite_actions_reusable_workflows_and_duplicate_occurrences(self):
        before = counters.snapshot(self.workspace)
        self.write("runs:\n  using: composite\n  steps:\n    - uses: owner/action@main\n"
                   "    - uses: owner/action@main\n    - run: echo '${{ inputs.message }}'\n"
                   "jobs: {decoy: {uses: ignored@main}}\n", "nested/action.yaml")
        self.write("jobs: {reusable: {uses: owner/repo/.github/workflows/demo.yml@main}}\n")
        rules = self.measure(before)["rules"]
        self.assertEqual(rules["unpinned_actions"]["count"], 3)
        self.assertEqual(rules["event_input_in_run"]["count"], 1)

    def test_invalid_bounded_or_symlinked_yaml_is_unknown(self):
        before = counters.snapshot(self.workspace)
        for source in ("jobs: [", "jobs: {}\njobs: {}\n", "x: &x [*x]\n", "jobs: {j: {uses: []}}"):
            with self.subTest(source=source):
                self.write(source)
                entry = self.measure(before)["rules"]["unpinned_actions"]
                self.assertEqual(entry["status"], "unknown")
                self.assertIsNone(entry["count"])
        path = self.write("jobs: {}")
        with mock.patch.object(counters, "MAX_FILE_BYTES", 2):
            self.assertIsNone(self.measure(before)["rules"]["unpinned_actions"]["count"])
        path.unlink()
        path.symlink_to(Path(self.temp.name) / "outside.yml")
        self.assertIsNone(self.measure(before)["rules"]["unpinned_actions"]["count"])
        path.unlink()
        for directory in ("a", "z"):
            self.write("runs: {using: composite, steps: []}", f"{directory}/action.yml")

        def reverse_directory_walk(*_args, **_kwargs):
            directories = ["z", "a"]
            yield str(self.workspace), directories, []
            # Like os.walk, subsequent descent respects the caller's mutation.
            for directory in directories:
                yield str(self.workspace / directory), [], ["action.yml"]

        import os
        with mock.patch.object(os, "walk", reverse_directory_walk), \
                mock.patch.object(counters, "MAX_FILES", 1):
            bounded = counters.snapshot(self.workspace)
        self.assertEqual(list(bounded["files"]), ["a/action.yml"])
        self.assertFalse(bounded["complete"])

        self.write("jobs: {}", ".github/workflows/a.yml")
        self.write("jobs: {}", ".github/workflows/z.yml")
        listing = [(str(self.workspace / ".github/workflows"), [], ["z.yml", "a.yml"])]
        with mock.patch.object(os, "walk", return_value=iter(listing)), \
                mock.patch.object(counters, "MAX_FILES", 1):
            bounded = counters.snapshot(self.workspace)
        self.assertEqual(list(bounded["files"]), [".github/workflows/a.yml"])

    def test_failed_pushes_do_not_count_and_typical_successful_push_does(self):
        rules = self.measure(evidence=trace(("git push -u origin feat/demo", True),
                                          "git push -u origin feat/demo"))["rules"]
        self.assertEqual(rules["push_without_verification"]["count"], 1)

    def test_exact_successful_subsequent_verification_is_required(self):
        push = f"git push origin {SHA}:feat/demo"
        check = f"git merge-base --is-ancestor {SHA} origin/feat/demo"
        for evidence, expected in (
                (trace(push, check), 0),
                (trace(check, push), 1),
                (trace(push, (check, True)), 1),
                (trace(push, check.replace(SHA, OTHER_SHA)), 1),
                (trace(push, check.replace("feat/demo", "feat/other")), 1)):
            with self.subTest(expected=expected, evidence=evidence):
                self.assertEqual(self.measure(evidence=evidence)["rules"]["push_without_verification"]["count"], expected)

    def test_branch_verification_without_sha_binding_is_unknown(self):
        evidence = trace("git push -u origin feat/demo",
                         f"git merge-base --is-ancestor {SHA} origin/feat/demo")
        self.assertIsNone(self.measure(evidence=evidence)["rules"]["push_without_verification"]["count"])

    def test_incomplete_missing_dynamic_or_compound_traces_are_unknown(self):
        samples = [None, trace("git push origin $branch"),
                   trace("git push origin feat/demo; echo done"),
                   trace("git -C repo push origin feat/demo"),
                   trace("/usr/bin/git push origin feat/demo"),
                   trace("command git push origin feat/demo"),
                   trace("env git push origin feat/demo"),
                   trace("unused() { git push origin feat/demo; }"),
                   trace("git push"), trace("bash -c 'git push origin feat/demo'")]
        capped = trace("git push origin feat/demo")
        capped["omitted_events"] = 2
        samples.append(capped)
        unmatched = trace("git push origin feat/demo")
        unmatched["events"].pop()
        samples.append(unmatched)
        clipped = trace("git push origin feat/demo")
        clipped["events"][0]["input_chars"] = 300
        samples.append(clipped)
        redacted = trace("git push origin feat/demo")
        redacted["events"][1]["output_incomplete"] = True
        samples.append(redacted)
        for evidence in samples:
            with self.subTest(evidence=evidence):
                self.assertIsNone(counters.measure(counters.snapshot(self.workspace), self.workspace, evidence)
                                  ["rules"]["push_without_verification"]["count"])

    def test_bash_ast_does_not_execute_comments_or_heredoc_text(self):
        for source in ("# git push origin feat/demo\necho harmless",
                       "cat <<'EOF'\ngit push origin feat/demo\nEOF"):
            entry = self.measure(evidence=trace(source))["rules"]["push_without_verification"]
            self.assertEqual(entry["observed_count"], 0)

    def test_redacted_trace_records_evidence_loss_without_secret_content(self):
        payload = [{"type": "assistant", "message": {"content": [
            {"type": "tool_use", "id": "tool-1", "name": "Bash",
             "input": {"command": "git push origin '" + "sensitive-value" + "'"}}]}},
            {"type": "user", "message": {"content": [
                {"type": "tool_result", "tool_use_id": "tool-1", "content": "sensitive-value"}]}}]
        events = cli_json.tool_events(payload, ["sensitive-value"])
        self.assertTrue(events[0]["input_incomplete"])
        self.assertTrue(events[1]["output_incomplete"])
        self.assertNotIn("sensitive-value", json.dumps(events))
        entry = self.measure(evidence=cli_json.bounded_tool_trace([events]))["rules"]["push_without_verification"]
        self.assertIsNone(entry["count"])

    def test_aggregation_includes_error_trials_and_missing_denominators(self):
        measured = self.measure(evidence=trace("git push origin feat/demo"))
        unknown = counters.measure(None, None, None)
        trials = [{"guidance_violations": measured, "error": {"type": "agent_error"}},
                  {"guidance_violations": unknown}, {}]
        block = run_eval.aggregate_trials(trials)["aggregate"]["guidance_violations"]
        self.assertEqual(block["push_without_verification"],
                         {"section_id": counters.RULES["push_without_verification"],
                          "n": 1, "n_missing": 2, "sum": 1})
        self.assertIsNone(counters.aggregate([{}]))

    def test_single_multi_and_guidance_reports_show_unknown_denominators(self):
        trial = {"arm": "without_skill", "error": None,
                 "guidance_violations": self.measure(evidence=trace("git push origin feat/demo"))}
        single = run_eval._render_report("demo", "prompt", "stamp", [trial])
        multi = run_eval._render_trials_report("demo", "stamp", 2, [{"label": "demo", "prompt": "prompt",
            "arms": [{"arm": "without_skill", "stats": run_eval.aggregate_trials([trial, {}])}]}])
        guidance = run_eval._render_guidance_report("git-practices", "prompt", "stamp", "user", {},
                                                   [{**trial, "mode": "none"}])
        for report in (single, multi, guidance):
            self.assertIn("push_without_verification (git-push-does-not-mean-commit-exists)", report)
        self.assertIn("1 / 1; 1 unknown", multi)

    def args(self):
        return argparse.Namespace(results_dir=Path(self.temp.name) / "results", timeout=None,
                                  no_judge=True, model=None, permission_mode="auto")

    def fixture(self):
        return run_eval.apply_runtime_subject({"subject": "any", "prompt": "fix"},
                                               "demo", None, "without_skill", Path("fixture.yaml"))

    def test_skill_runner_records_agent_and_scorer_errors_before_cleanup(self):
        fixture, args = self.fixture(), self.args()
        for scorer_error in (False, True):
            self.workspace.mkdir(exist_ok=True)
            output = Path(self.temp.name) / ("scorer" if scorer_error else "agent")
            def agent(*_args):
                self.write(workflow("      - uses: owner/action@main\n"))
                return ({"error": "agent_error"} if not scorer_error else {}) | {"tool_trace": trace("git push origin feat/demo")}
            with mock.patch.object(run_eval, "materialize_workspace", return_value=self.workspace), \
                    mock.patch.object(run_eval, "assert_stand_ins_on_path"), \
                    mock.patch.object(run_eval, "run_agent", side_effect=agent), \
                    mock.patch.object(run_eval.objective, "run_checks", side_effect=run_eval.objective.ScorerUnavailableError("unavailable")):
                result = run_eval._run_arm("without_skill", fixture, self.workspace, {}, args, "stamp",
                                           (None, None, None), out_dir=output)
            written = json.loads((output / "summary.json").read_text())
            self.assertEqual(written["guidance_violations"], result["guidance_violations"])
            self.assertEqual(written["guidance_violations"]["rules"]["unpinned_actions"]["count"], 1)
            self.assertEqual(written["guidance_violations"]["rules"]["push_without_verification"]["count"], 1)

    def test_pre_agent_refusal_is_unknown_in_summary_and_report(self):
        fixture, args = self.fixture(), self.args()
        output = Path(self.temp.name) / "refusal"
        with mock.patch.object(run_eval, "materialize_workspace") as materialize:
            result = run_eval._run_arm("without_skill", fixture, self.workspace, {}, args, "stamp",
                                       (None, None, "refused"), out_dir=output)
        materialize.assert_not_called()
        written = json.loads((output / "summary.json").read_text())
        self.assertEqual(written["guidance_violations"], result["guidance_violations"])
        for entry in written["guidance_violations"]["rules"].values():
            self.assertIsNone(entry["count"])
        self.assertIn("unknown", run_eval._render_report("demo", "prompt", "stamp", [result]))

    def test_guidance_trial_attaches_counters_before_scorer_failure(self):
        fixture = run_eval.apply_runtime_subject({"subject": "any", "prompt": "fix"},
                                                None, "git-practices", "both", Path("fixture.yaml"))
        arm = {"name": "none", "mode": "none", "objective_checks": []}
        ctx = {"delivery": "user", "section": "git-practices", "key": "guidance/git-practices/demo",
               "token": "demo", "decoys": {"none": "decoy"}, "row": {}, "guidance_dir": self.workspace}
        args = self.args()
        def agent(workspace, *_args):
            target = workspace / WORKFLOW
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(workflow("      - uses: owner/action@main\n"), encoding="utf-8")
            return {"tool_trace": trace("git push origin feat/demo")}
        with mock.patch.object(run_eval, "_git"), \
                mock.patch.object(run_eval.guidance, "assemble", return_value="payload"), \
                mock.patch.object(run_eval.guidance, "deliver", return_value={"bytes": 7, "verdict": "ok", "installed": True, "returncode": 0}), \
                mock.patch.object(run_eval.guidance, "run_guard", return_value={"ok": True}), \
                mock.patch.object(run_eval, "run_agent", side_effect=agent), \
                mock.patch.object(run_eval.objective, "run_checks", side_effect=run_eval.objective.ScorerUnavailableError("unavailable")):
            result = run_eval._run_guidance_arm(arm, fixture, self.workspace, ctx, args, "stamp")
        written = json.loads((args.results_dir / ctx["key"] / "stamp" / "none" / "summary.json").read_text())
        self.assertEqual(written["guidance_violations"], result["guidance_violations"])
        self.assertEqual(written["guidance_violations"]["rules"]["unpinned_actions"]["count"], 1)
        self.assertEqual(written["guidance_violations"]["rules"]["push_without_verification"]["count"], 1)

    def test_guidance_setup_failure_has_unknown_counters(self):
        fixture = {"_real_work": True, "subject": "guidance", "section": "git-practices"}
        arm = {"name": "none", "mode": "none"}
        ctx = {"section": "git-practices", "key": "guidance/git-practices/demo"}
        args = self.args()
        with mock.patch.object(run_eval.seed_prep, "prepare_seed", side_effect=run_eval.guidance.GuidanceError("unavailable")):
            result = run_eval._run_guidance_arm(arm, fixture, self.workspace, ctx, args, "stamp")
        written = json.loads((args.results_dir / ctx["key"] / "stamp" / "none" / "summary.json").read_text())
        self.assertEqual(written["guidance_violations"], result["guidance_violations"])
        self.assertEqual(written["guidance_violations"]["rules"]["unpinned_actions"]["status"], "unknown")


if __name__ == "__main__":
    unittest.main()
