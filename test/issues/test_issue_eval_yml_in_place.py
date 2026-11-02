#!/usr/bin/env python3
"""ADR 0012: `eval.yml`'s `eval` job runs in-place fixtures like the routine.

An in-place fixture (a top-level `context:` mapping in fixture.yaml) needs
every context repository cloned beside skills-evals with full history, and
`--pairing in_place` on run_eval.py. Pinned here, from the parsed workflow:

  * for every `context.repository` any committed fixture names, the `eval`
    job checks that repository out at `path: <name>` with `fetch-depth: 0`
    and `persist-credentials: false` (skills-evals itself is the first
    checkout);
  * the "Run the eval" step decides pairing with `declares_context` and
    passes `--pairing "$pairing"`;
  * bubblewrap and socat are provided for the arm sandbox before the token
    exchange.
"""

from __future__ import annotations

import unittest
from pathlib import Path

import yaml

TEST_DIR = Path(__file__).resolve().parent.parent
REPO_ROOT = TEST_DIR.parent
EVAL_WORKFLOW = REPO_ROOT / ".github" / "workflows" / "eval.yml"
RUN_STEP = "Run the eval (both arms, judge)"
SELF = "skills-evals"


def eval_steps():
    # PyYAML reads the `on:` key as True; only `jobs` is used here.
    document = yaml.safe_load(EVAL_WORKFLOW.read_text(encoding="utf-8"))
    return document["jobs"]["eval"]["steps"]


def context_repositories():
    names = set()
    for path in sorted((REPO_ROOT / "evals").rglob("fixture.yaml")):
        document = yaml.safe_load(path.read_text(encoding="utf-8"))
        context = document.get("context") if isinstance(document, dict) else None
        if isinstance(context, dict) and context.get("repository"):
            names.add(str(context["repository"]).rsplit("/", 1)[-1])
    return names


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

    def test_run_step_passes_pairing_decided_by_declares_context(self):
        steps = [s for s in eval_steps() if s.get("name") == RUN_STEP]
        self.assertEqual(len(steps), 1)
        script = steps[0]["run"]
        self.assertIn("declares_context", script)
        self.assertIn('--pairing "$pairing"', script)


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
