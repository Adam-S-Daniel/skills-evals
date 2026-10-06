#!/usr/bin/env python3
"""Issue #71 / ADR 0010: the dispatch-only workflow that fires the eval routine.

`.github/workflows/routine-eval-fire.yml` fires
https://claude.ai/code/routines/trig_014cqgegCtJUqXYjAKmkr4J5 through the
routines fire API. What is pinned here:

  * it triggers on `workflow_dispatch` only (no schedule: #71's gate; no
    pull_request: it would have to be a required check), with exactly the
    inputs fixture, arms and trials, and `permissions: contents: read`;
  * every `uses:` is a 40-character SHA with nothing after it on the line,
    at the same SHA this repo's other workflows already pin;
  * no `${{ inputs.* }}` or `${{ github.event.* }}` inside any `run:` block;
  * `secrets.EVAL_ROUTINE_FIRE_BEARER` appears only as a step `env` value,
    on the fire step, which runs after the validation step;
  * the validation step, run for real, accepts a committed fixture and
    refuses `..`, paths outside evals/, uncommitted fixtures and bad arms or
    trials without echoing the value, and emits a run id of the agreed shape;
  * the fire step, run against a fake curl, sends the bearer on stdin (never
    argv) and a payload of exactly four fields, and never prints the
    response body, on success or failure.

The workflow is parsed with PyYAML, never scanned line by line. Discovered
and run by test/run_tests.py; also runnable on its own with
`python3 test/issues/test_issue_routine_eval_fire.py`.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import stat
import subprocess
import tempfile
import unittest
from pathlib import Path

import yaml

TEST_DIR = Path(__file__).resolve().parent.parent
REPO_ROOT = TEST_DIR.parent
WORKFLOWS = REPO_ROOT / ".github" / "workflows"
WORKFLOW = WORKFLOWS / "routine-eval-fire.yml"

SECRET_REF = "secrets.EVAL_ROUTINE_FIRE_BEARER"
RUN_ID = re.compile(r"^[0-9]{8}T[0-9]{6}Z-[0-9a-f]{6}$")
FIXTURE = "evals/writing-adrs/bootstrap"
# A lexical check on the expression token only, applied to a `run:` value
# the parser already isolated.
FORBIDDEN_IN_RUN = re.compile(r"\$\{\{[^}]*\b(?:inputs\.|github\.event\.)")


def load(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def triggers(doc: dict):
    # A bare `on:` key is the YAML 1.1 boolean True once parsed.
    return doc.get("on", doc.get(True))


def scalars(node, path=()):
    """Every string scalar in a parsed document, with its key path."""
    if isinstance(node, dict):
        for key, value in node.items():
            yield from scalars(value, path + (key,))
    elif isinstance(node, list):
        for index, value in enumerate(node):
            yield from scalars(value, path + (index,))
    elif isinstance(node, str):
        yield path, node


def uses_nodes(node):
    """Every `uses:` value node in a composed YAML tree, with its marks."""
    if isinstance(node, yaml.MappingNode):
        for key, value in node.value:
            if isinstance(key, yaml.ScalarNode) and key.value == "uses":
                yield value
            yield from uses_nodes(value)
    elif isinstance(node, yaml.SequenceNode):
        for item in node.value:
            yield from uses_nodes(item)


class WorkflowShapeTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.text = WORKFLOW.read_text(encoding="utf-8")
        cls.doc = yaml.safe_load(cls.text)
        cls.job = cls.doc["jobs"]["fire"]
        cls.steps = cls.job["steps"]

    def test_only_workflow_dispatch(self):
        on = triggers(self.doc)
        self.assertIsInstance(on, dict)
        self.assertEqual(set(on), {"workflow_dispatch"},
                         "dispatch only: no schedule (#71's gate), no "
                         "pull_request or push (it would need a required check)")
        self.assertEqual(set(on["workflow_dispatch"]["inputs"]),
                         {"fixture", "arms", "trials"})
        self.assertEqual(on["workflow_dispatch"]["inputs"]["arms"]["options"],
                         ["both", "with", "without"])
        self.assertEqual(on["workflow_dispatch"]["inputs"]["trials"]["options"],
                         ["1", "2", "3"])

    def test_permissions_are_contents_read(self):
        self.assertEqual(self.doc.get("permissions"), {"contents": "read"})
        for name, job in self.doc["jobs"].items():
            self.assertNotIn("permissions", job,
                             f"job {name} must not widen the workflow's permissions")

    def test_only_the_default_branch_copy_can_fire(self):
        self.assertEqual(
            self.job.get("if"),
            "github.ref == format('refs/heads/{0}', "
            "github.event.repository.default_branch)")

    def test_every_uses_is_a_bare_sha_already_pinned_elsewhere(self):
        pinned_elsewhere = set()
        for other in WORKFLOWS.glob("*.yml"):
            if other == WORKFLOW:
                continue
            for node in uses_nodes(yaml.compose(other.read_text(encoding="utf-8"))):
                pinned_elsewhere.add(node.value)
        lines = self.text.splitlines()
        nodes = list(uses_nodes(yaml.compose(self.text)))
        self.assertTrue(nodes, "expected at least one uses:")
        for node in nodes:
            with self.subTest(uses=node.value):
                self.assertRegex(node.value, r"^[^@\s]+@[0-9a-f]{40}$")
                self.assertEqual(node.start_mark.line, node.end_mark.line)
                rest = lines[node.end_mark.line][node.end_mark.column:]
                self.assertEqual(rest.strip(), "",
                                 "a pin carries no trailing version comment")
                self.assertIn(node.value, pinned_elsewhere,
                              "reuse an action at the SHA this repo already pins")

    def test_no_inputs_or_event_expressions_in_run_blocks(self):
        runs = [(p, v) for p, v in scalars(self.doc) if p and p[-1] == "run"]
        self.assertTrue(runs)
        for path, value in runs:
            with self.subTest(path=path):
                self.assertIsNone(FORBIDDEN_IN_RUN.search(value),
                                  "read dispatch inputs from $GITHUB_EVENT_PATH")

    def test_secret_is_referenced_only_in_the_fire_step_env(self):
        hits = [p for p, v in scalars(self.doc) if SECRET_REF in v]
        fire = next(i for i, s in enumerate(self.steps)
                    if s.get("name") == "Fire the eval routine")
        self.assertEqual(hits, [("jobs", "fire", "steps", fire, "env",
                                 "EVAL_ROUTINE_FIRE_BEARER")])
        self.assertNotIn("secrets.", self.steps[fire]["run"])
        mentions = [p for p, v in scalars(self.doc) if "secrets." in v]
        self.assertEqual(mentions, hits, "no other secret is referenced")

    def test_validation_step_runs_before_the_fire_step(self):
        ids = [s.get("id") for s in self.steps]
        self.assertIn("validate", ids)
        fire = next(i for i, s in enumerate(self.steps)
                    if s.get("name") == "Fire the eval routine")
        self.assertLess(ids.index("validate"), fire)
        env = self.steps[fire]["env"]
        for key, output in (("RUN_ID", "run_id"), ("FIXTURE", "fixture"),
                            ("ARMS", "arms"), ("TRIALS", "trials")):
            self.assertEqual(env[key], f"${{{{ steps.validate.outputs.{output} }}}}")
        self.assertEqual(
            env["FIRE_URL"],
            "https://api.anthropic.com/v1/claude_code/routines/"
            "trig_014cqgegCtJUqXYjAKmkr4J5/fire")

    def test_checkout_does_not_persist_credentials(self):
        checkout = [s for s in self.steps
                    if str(s.get("uses", "")).startswith("actions/checkout@")]
        self.assertEqual(len(checkout), 1)
        self.assertIs(checkout[0]["with"]["persist-credentials"], False)


def step_script(name: str) -> str:
    steps = load(WORKFLOW)["jobs"]["fire"]["steps"]
    return next(s for s in steps if s.get("name") == name)["run"]


@unittest.skipUnless(shutil.which("jq") and shutil.which("git"),
                     "needs jq and git on PATH")
class ValidateStepTests(unittest.TestCase):

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp)
        self.script = step_script("Validate the dispatch inputs")

    def run_step(self, inputs):
        event = self.tmp / "event.json"
        event.write_text(json.dumps({"inputs": inputs}), encoding="utf-8")
        output = self.tmp / "output"
        output.write_text("", encoding="utf-8")
        env = {"PATH": os.environ["PATH"], "HOME": str(self.tmp),
               "GITHUB_EVENT_PATH": str(event), "GITHUB_OUTPUT": str(output)}
        proc = subprocess.run(["bash", "-c", self.script], cwd=REPO_ROOT,
                              env=env, capture_output=True, text=True,
                              timeout=60)
        values = dict(line.split("=", 1) for line in
                      output.read_text(encoding="utf-8").splitlines())
        return proc, values

    def test_accepts_a_committed_fixture(self):
        proc, values = self.run_step(
            {"fixture": FIXTURE, "arms": "with", "trials": "3"})
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertEqual(values["fixture"], FIXTURE)
        self.assertEqual((values["arms"], values["trials"]), ("with", "3"))
        self.assertRegex(values["run_id"], RUN_ID)

    def test_refuses_bad_inputs_without_echoing_them(self):
        good = {"fixture": FIXTURE, "arms": "both", "trials": "1"}
        cases = {
            "dotdot": {"fixture": "evals/../evals/writing-adrs/bootstrap"},
            "dot": {"fixture": "evals/./writing-adrs/bootstrap"},
            "outside_evals": {"fixture": "harness"},
            "uncommitted": {"fixture": "evals/no-such-fixture-xyz"},
            "prefix_only": {"fixture": "evals/writing-adrs"},
            "multiline": {"fixture": FIXTURE + "\nevals/browser-testing"},
            "shell_chars": {"fixture": "evals/$(id)"},
            "nul": {"fixture": FIXTURE + "\u0000"},
            "empty": {"fixture": ""},
            "arms": {"arms": "all-of-them"},
            "trials_high": {"trials": "4"},
            "trials_zero": {"trials": "0"},
            "trials_number": {"trials": 2},
            "missing": {"arms": None},
        }
        for label, override in cases.items():
            with self.subTest(case=label):
                inputs = {**good, **override}
                inputs = {k: v for k, v in inputs.items() if v is not None}
                proc, values = self.run_step(inputs)
                self.assertNotEqual(proc.returncode, 0)
                self.assertNotIn("run_id", values)
                bad = next(iter(override.values()))
                if isinstance(bad, str) and bad:
                    self.assertNotIn(bad, proc.stdout + proc.stderr)


FAKE_CURL = """#!/usr/bin/env python3
import json, os, sys
log = os.environ["FAKE_CURL_LOG"]
args = sys.argv[1:]
with open(os.path.join(log, "argv.json"), "w") as f:
    json.dump(args, f)
with open(os.path.join(log, "stdin"), "w") as f:
    f.write(sys.stdin.read())
with open(os.path.join(log, "calls"), "a") as f:
    f.write("call\\n")
with open(args[args.index("--output") + 1], "w") as f:
    f.write(os.environ["FAKE_CURL_BODY"])
sys.stdout.write(os.environ["FAKE_CURL_STATUS"])
sys.exit(int(os.environ.get("FAKE_CURL_EXIT", "0")))
"""


class FireStepTests(unittest.TestCase):

    BEARER = "sk-ant-oat01-FAKE-BEARER-FOR-TESTS"
    SESSION = "session_01TestOnlyAbc"

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp)
        self.bin = self.tmp / "bin"
        self.bin.mkdir()
        curl = self.bin / "curl"
        curl.write_text(FAKE_CURL, encoding="utf-8")
        curl.chmod(curl.stat().st_mode | stat.S_IXUSR)
        self.log = self.tmp / "log"
        self.log.mkdir()
        self.summary = self.tmp / "summary.md"
        self.script = step_script("Fire the eval routine")
        self.env_block = next(
            s for s in load(WORKFLOW)["jobs"]["fire"]["steps"]
            if s.get("name") == "Fire the eval routine")["env"]

    def run_step(self, status, body, curl_exit=0):
        self.summary.write_text("", encoding="utf-8")
        (self.log / "calls").unlink(missing_ok=True)
        env = {
            "FAKE_CURL_EXIT": str(curl_exit),
            "PATH": f"{self.bin}{os.pathsep}{os.environ['PATH']}",
            "HOME": str(self.tmp),
            "FIRE_URL": self.env_block["FIRE_URL"],
            "EVAL_ROUTINE_FIRE_BEARER": self.BEARER,
            "RUN_ID": "20261006T120000Z-a1b2c3",
            "FIXTURE": FIXTURE, "ARMS": "both", "TRIALS": "2",
            "GITHUB_STEP_SUMMARY": str(self.summary),
            "FAKE_CURL_LOG": str(self.log),
            "FAKE_CURL_STATUS": status, "FAKE_CURL_BODY": body,
        }
        return subprocess.run(["bash", "-c", self.script], cwd=self.tmp,
                              env=env, capture_output=True, text=True,
                              timeout=60)

    def ok_body(self, **extra):
        return json.dumps({
            "type": "routine_fire",
            "claude_code_session_id": self.SESSION,
            "claude_code_session_url": f"https://claude.ai/code/{self.SESSION}",
            **extra})

    @unittest.skipUnless(shutil.which("jq"), "needs jq on PATH")
    def test_success_sends_four_fields_and_keeps_the_bearer_off_argv(self):
        proc = self.run_step("200", self.ok_body(note="BODY-SENTINEL"))
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        argv = json.loads((self.log / "argv.json").read_text())
        self.assertFalse(any(self.BEARER in a for a in argv))
        self.assertIn("anthropic-version: 2023-06-01", argv)
        self.assertEqual(argv[argv.index("--header") + 1], "@-")
        self.assertEqual((self.log / "stdin").read_text(),
                         f"Authorization: Bearer {self.BEARER}\n")
        body = json.loads(argv[argv.index("--data-binary") + 1])
        self.assertEqual(set(body), {"text"})
        self.assertEqual(json.loads(body["text"]), {
            "run_id": "20261006T120000Z-a1b2c3", "fixture": FIXTURE,
            "arms": "both", "trials": 2})
        out = proc.stdout + proc.stderr
        self.assertNotIn(self.BEARER, out)
        self.assertNotIn("BODY-SENTINEL", out)
        self.assertNotIn(self.SESSION, out, "the session link goes to the summary only")
        self.assertIn("20261006T120000Z-a1b2c3", out)
        summary = self.summary.read_text()
        self.assertIn(f"https://claude.ai/code/{self.SESSION}", summary)
        self.assertIn("claude/eval-20261006T120000Z-a1b2c3", summary)

    @unittest.skipUnless(shutil.which("jq"), "needs jq on PATH")
    def test_failures_print_only_the_status(self):
        cases = {
            "http_401": ("401", '{"type":"error","error":{"message":"BODY-SENTINEL"}}'),
            "bad_type": ("200", self.ok_body(type="BODY-SENTINEL")),
            "bad_id": ("200", json.dumps({
                "type": "routine_fire",
                "claude_code_session_id": "BODY-SENTINEL; rm",
                "claude_code_session_url": "https://claude.ai/code/x"})),
            "url_mismatch": ("200", self.ok_body(
                claude_code_session_url="https://example.com/BODY-SENTINEL")),
            "not_json": ("200", "BODY-SENTINEL"),
            "http_500": ("500", '{"type":"error","error":{"message":"BODY-SENTINEL"}}'),
        }
        for label, (status, body) in cases.items():
            with self.subTest(case=label):
                proc = self.run_step(status, body)
                self.assertNotEqual(proc.returncode, 0)
                out = proc.stdout + proc.stderr
                self.assertIn(f"status: {status}", out)
                self.assertNotIn("BODY-SENTINEL", out)
                self.assertNotIn(self.BEARER, out)
                self.assertEqual(self.summary.read_text(), "")

    @unittest.skipUnless(shutil.which("jq"), "needs jq on PATH")
    def test_a_curl_failure_is_status_000_and_prints_no_body(self):
        # curl exits nonzero with `%{http_code}` already written as 000 on a
        # refused connection or a timeout, and writes nothing on a spawn
        # failure; both must read as 000.
        for label, printed, code in (("timeout", "000", 28), ("no_output", "", 7)):
            with self.subTest(case=label):
                proc = self.run_step(printed, "BODY-SENTINEL", curl_exit=code)
                self.assertNotEqual(proc.returncode, 0)
                out = proc.stdout + proc.stderr
                self.assertIn("fire API status: 000", out)
                self.assertIn("the fire API answered 000", out)
                self.assertNotIn("BODY-SENTINEL", out)
                self.assertNotIn(self.BEARER, out)
                self.assertEqual(self.summary.read_text(), "")

    @unittest.skipUnless(shutil.which("jq"), "needs jq on PATH")
    def test_it_never_retries(self):
        # The fire API has no idempotency key: a second request after a lost
        # response would start a second session. Exactly one curl call, on
        # success and on every failure.
        cases = {
            "success": ("200", self.ok_body(), 0),
            "http_500": ("500", "BODY-SENTINEL", 0),
            "http_429": ("429", "BODY-SENTINEL", 0),
            "http_401": ("401", "BODY-SENTINEL", 0),
            "curl_failure": ("000", "", 28),
            "bad_body": ("200", "BODY-SENTINEL", 0),
        }
        for label, (status, body, code) in cases.items():
            with self.subTest(case=label):
                self.run_step(status, body, curl_exit=code)
                calls = (self.log / "calls").read_text().splitlines()
                self.assertEqual(calls, ["call"])

    def test_the_workflow_asks_for_no_retry(self):
        doc = load(WORKFLOW)
        self.assertNotIn("--retry", self.script)
        self.assertNotIn("--retry-all-errors", self.script)
        for path, value in scalars(doc):
            if path[-1] in ("run",):
                continue
            self.assertNotRegex(str(value), r"(?i)\bretry\b")
        for key_path in (("jobs", "fire"),):
            node = doc
            for key in key_path:
                node = node[key]
            self.assertNotIn("strategy", node)


if __name__ == "__main__":
    unittest.main()
