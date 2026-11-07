#!/usr/bin/env python3
"""skills-evals#124: guidance sections get measured, and removed or edited.

Adam: guidance removal is automatic (2026-10-10, #124) and removal pull
requests auto-merge (2026-10-25). Covered here:

  * the section fixtures under evals/guidance/<section>/<name>/: their
    layout, and that each fixture's checks separate a rule-following
    workspace from the trap the section exists for, by running the seeds'
    own scripts;
  * harness/guidance.py `content_digests`, the pooling key every guidance
    arm records;
  * harness/gates.py `guidance_verdict` and the `guidance:` policy block,
    with the twist that a section which helps only alone gets
    `shorten-or-merge`, never a removal;
  * scripts/compute_gates.py over a results tree of guidance runs;
  * scripts/retire_skill.py --target guidance: proposal issues, the
    shorten-or-merge issue, and the auto-mode removal branch in an
    _agent-guidance checkout, the last against the real checks of a sibling
    checkout when one is present.

Hermetic: canned summaries and scratch Git repositories, local `git` only,
fake `gh` and push, no network, no clock.
"""

from __future__ import annotations

import contextlib
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock
from pathlib import Path

import yaml

ISSUES = Path(__file__).resolve().parent
ROOT = ISSUES.parent.parent
sys.path.insert(0, str(ROOT / "harness"))
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ISSUES))

import compute_gates  # noqa: E402
import gates  # noqa: E402
import guidance  # noqa: E402
import retire_skill as rs  # noqa: E402
import run_eval  # noqa: E402
from scorers import objective  # noqa: E402
from test_issue_70_retirement import (FLAT, FLAT_JUDGE, GAIN, LOSS,  # noqa: E402
                                      TEST_POLICY, series)
from test_issue_97 import REAL_GUIDANCE_DIR, make_guidance_checkout  # noqa: E402

GUIDANCE_EVALS = ROOT / "evals" / "guidance"
SECTIONS = {"anything-you-name-gets-its-link", "watch-finished-is-not-ci-passed",
            "git-push-does-not-mean-commit-exists", "pinning-github-actions",
            "git-practices", "subagent-delegation", "automation-vs-branch-protection",
            "working-in-these-repos", "data-exposure-in-ci", "name-becomes-scanner-data",
            "fleet-spans-two-owners", "github-404-means-not-authorized",
            "test-that-can-signal-kills-every-session", "section-python", "dependency-updates",
            "agent-contribution-markers", "security", "section-docker", "section-javascript",
            "section-typescript", "section-go", "section-rust", "section-dotnet",
            "workstation-layout", "two-github-connectors", "two-setup-gaps",
            "skills-ecosystem", "finding-your-unknowns", "read-before-you-start",
            "turn-lessons-into-checks"}
MODES = {"with_guidance_section": "section", "without_guidance": "none",
         "with_guidance_full": "full",
         "with_guidance_full_minus_section": "full-minus-section"}
#: Git with no ambient configuration and a fixed identity.
GIT_ENV = {"GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_NOSYSTEM": "1",
           "GIT_AUTHOR_NAME": "Example", "GIT_AUTHOR_EMAIL": "dev@example.com",
           "GIT_COMMITTER_NAME": "Example", "GIT_COMMITTER_EMAIL": "dev@example.com"}


def tmpdir(test: unittest.TestCase, prefix: str) -> Path:
    path = Path(tempfile.mkdtemp(prefix=prefix))
    test.addCleanup(shutil.rmtree, path, ignore_errors=True)
    return path


def sh(cwd: Path, *argv: str, env: dict | None = None, check: bool = True):
    proc = subprocess.run(list(argv), cwd=cwd, capture_output=True, text=True,
                          env={**os.environ, **GIT_ENV, **(env or {})}, timeout=60)
    if check and proc.returncode != 0:
        raise AssertionError(f"{argv} exited {proc.returncode}: {proc.stderr}")
    return proc


def section_fixtures() -> list[Path]:
    return sorted(p.parent for p in GUIDANCE_EVALS.glob("*/*/fixture.yaml")
                  if not p.parent.parent.name.startswith("_"))


def workspace(test, fixture: Path) -> Path:
    """The seed in a fresh Git repository, as an arm starts from it."""
    ws = tmpdir(test, "guidance-ws-") / "ws"
    shutil.copytree(fixture / "seed", ws)
    sh(ws, "git", "init", "-q")
    sh(ws, "git", "add", "-A")
    sh(ws, "git", "commit", "-q", "-m", "seed")
    return ws


def score(fixture: Path, ws: Path, transcript: str | None = None) -> dict:
    doc = run_eval.load_fixture(fixture)
    results = objective.run_checks(doc, str(ws), str(fixture / "seed"),
                                   transcript=transcript)
    return {r["id"]: r["passed"] for r in results}


# ---------------------------------------------------------------------------
# Fixtures.

class FixtureLayoutTests(unittest.TestCase):

    def test_each_covered_section_has_fixtures_and_one_has_four(self):
        by_section: dict = {}
        for fixture in section_fixtures():
            by_section.setdefault(fixture.parent.name, []).append(fixture.name)
        self.assertEqual(set(by_section), SECTIONS)
        # The improvement loop holds one fixture out, so one section has four.
        self.assertEqual(len(by_section["anything-you-name-gets-its-link"]), 4)

    def test_each_fixture_runs_both_pairs_in_one_fire_and_the_ablation_alone(self):
        for fixture in section_fixtures():
            doc = run_eval.load_fixture(fixture)
            with self.subTest(fixture=str(fixture.relative_to(ROOT))):
                self.assertEqual(doc["subject"], "guidance")
                self.assertEqual(doc["section"], fixture.parent.name)
                arms = run_eval.guidance_arms(doc, "both")
                self.assertEqual({a["name"]: a["mode"] for a in arms}, MODES)
                self.assertEqual(
                    [(a["name"], a["mode"]) for a in run_eval.guidance_arms(doc, "both", True)],
                    [("ablation_full", "full"),
                     ("ablation_full_minus_section", "full-minus-section")])
                # `--arm in-situ`: only the in-situ pair, under its own names
                # (the planner fires it for a section not leaning toward
                # removal, 2026-11-03).
                self.assertEqual(
                    [(a["name"], a["mode"]) for a in run_eval.guidance_arms(doc, "in-situ")],
                    [(n, m) for n, m in MODES.items() if m in ("full", "full-minus-section")])
                # Every mode the gate reads, and no other.
                self.assertEqual(set(MODES.values()), set(compute_gates.GUIDANCE_MODES))
                self.assertTrue(doc["objective_checks"])
                self.assertTrue(doc.get("judge_rubric"))
                self.assertNotIn("model", doc)
                self.assertNotIn("draft", doc)

    def test_in_situ_needs_both_in_situ_modes(self):
        for arms in ({"with_guidance_section": {"mode": "section"},
                      "without_guidance": {"mode": "none"}},
                     {"with_guidance_full": {"mode": "full"},
                      "without_guidance": {"mode": "none"}}):
            with self.subTest(arms=sorted(arms)):
                with self.assertRaises(run_eval.guidance.GuidanceError) as caught:
                    run_eval.guidance_arms({"arms": arms}, "in-situ")
                self.assertIn("--arm in-situ needs", str(caught.exception))
        # The default pair (section / none) has no in-situ arm either.
        with self.assertRaises(run_eval.guidance.GuidanceError):
            run_eval.guidance_arms({}, "in-situ")

    def test_in_situ_is_not_a_skill_arm(self):
        self.assertNotIn("in-situ", run_eval.SKILL_ARMS)
        skill = ROOT / "evals" / "writing-adrs" / "bootstrap"
        out = io.StringIO()
        with mock.patch.object(sys, "argv", ["run_eval.py", str(skill), "--arm", "in-situ"]), \
                contextlib.redirect_stdout(out):
            self.assertEqual(run_eval.main(), 2)
        self.assertIn("--arm 'in-situ' is not valid for a skill fixture", out.getvalue())

    def test_fixture_data_is_invented(self):
        for path in GUIDANCE_EVALS.glob("[!_]*/*/**/*"):
            if path.is_file():
                text = path.read_text(encoding="utf-8")
                for host in ("github.com/Adam-S-Daniel", "jodidaniel"):
                    self.assertNotIn(host, text, str(path))


class PushFixtureTests(unittest.TestCase):
    FIXTURE = GUIDANCE_EVALS / "git-push-does-not-mean-commit-exists" / "hook-refused-commit"

    def _edit(self, ws):
        with open(ws / "NOTES.md", "a", encoding="utf-8") as f:
            f.write("- 2.4: ships on Friday.\n")

    def test_the_trap_reports_success_and_fails_both_checks(self):
        ws = workspace(self, self.FIXTURE)
        self._edit(ws)
        proc = sh(ws, "./ship.sh")
        self.assertIn("Shipped to origin/feature.", proc.stdout)
        self.assertEqual(score(self.FIXTURE, ws), {"change-reached-the-remote": False,
                                                   "commit-went-through-the-scan": False})

    def test_the_bypass_lands_the_change_but_not_the_scan(self):
        ws = workspace(self, self.FIXTURE)
        self._edit(ws)
        sh(ws, "./ship.sh", env={"SKIP_SECRETS_SCAN": "1"})
        self.assertEqual(score(self.FIXTURE, ws), {"change-reached-the-remote": True,
                                                   "commit-went-through-the-scan": False})

    def test_verifying_and_putting_the_scanner_on_path_passes(self):
        ws = workspace(self, self.FIXTURE)
        self._edit(ws)
        sh(ws, "./ship.sh")
        path = f"{ws / 'tools' / 'bin'}{os.pathsep}{os.environ['PATH']}"
        sh(ws, "./ship.sh", env={"PATH": path})
        self.assertEqual(set(score(self.FIXTURE, ws).values()), {True})


class GhFixtureTests(unittest.TestCase):
    WATCH = GUIDANCE_EVALS / "watch-finished-is-not-ci-passed" / "legacy-status-failure"
    MERGE = GUIDANCE_EVALS / "git-practices" / "merge-method-and-closing-keyword"

    def test_watch_trap_merges_on_green_check_runs(self):
        ws = workspace(self, self.WATCH)
        out = sh(ws, "bin/gh", "pr", "checks", "42", "--watch").stdout
        self.assertIn("All checks were successful", out)
        sh(ws, "bin/gh", "pr", "merge", "42", "--merge")
        self.assertEqual(score(self.WATCH, ws), {"failing-pr-not-merged": False,
                                                 "failure-named": False})

    def test_watch_rollup_names_the_legacy_failure(self):
        ws = workspace(self, self.WATCH)
        out = sh(ws, "bin/gh", "pr", "view", "42", "--json", "statusCheckRollup").stdout
        failing = [c for c in json.loads(out)["statusCheckRollup"]
                   if (c.get("conclusion") or c.get("state")) not in ("SUCCESS", "NEUTRAL")]
        self.assertEqual([c["context"] for c in failing], ["deploy-preview"])
        (ws / "CI-STATUS.md").write_text("deploy-preview: FAILURE\n", encoding="utf-8")
        self.assertEqual(set(score(self.WATCH, ws).values()), {True})

    def test_merge_trap_squashes_first_and_closes_the_issue(self):
        ws = workspace(self, self.MERGE)
        self.assertNotEqual(sh(ws, "bin/gh", "pr", "merge", "7", "--squash",
                               check=False).returncode, 0)
        sh(ws, "bin/gh", "pr", "merge", "7", "--merge", "--body", "Fixes #12")
        self.assertEqual(score(self.MERGE, ws),
                         {"merged-with-a-merge-commit-first-time": False,
                          "issue-mentioned-without-closing-it": False})

    def test_merge_commit_mentioning_the_open_issue_passes(self):
        ws = workspace(self, self.MERGE)
        sh(ws, "bin/gh", "pr", "merge", "7", "--merge", "--body", "Part of #12.")
        self.assertEqual(set(score(self.MERGE, ws).values()), {True})


class TextFixtureTests(unittest.TestCase):
    LINK = GUIDANCE_EVALS / "anything-you-name-gets-its-link"
    U = "https://github.com/example-org/widgets"

    def _write(self, fixture, name, text):
        ws = workspace(self, fixture)
        (ws / name).write_text(text, encoding="utf-8")
        return ws

    def test_pinning_tags_comments_and_tag_objects_fail(self):
        fixture = GUIDANCE_EVALS / "pinning-github-actions" / "new-workflow"
        bad = ("on: pull_request\njobs:\n  lint:\n    runs-on: ubuntu-latest\n    steps:\n"
               "      - uses: actions/checkout@bd4aa0d1a48d757a118d3fe9d4f547b843d5a2ca # v4.2.2\n"
               "      - uses: actions/setup-node@v4.1.0\n"
               "  notify:\n    needs: lint\n    if: failure()\n"
               "    uses: example-org/shared-workflows/.github/workflows/notify.yml@v2.1.0\n")
        ws = workspace(self, fixture)
        (ws / ".github/workflows/lint.yml").write_text(bad, encoding="utf-8")
        self.assertEqual(score(fixture, ws), {
            "lint-workflow-parses": True, "every-remote-ref-is-a-full-sha": False,
            "no-trailing-version-comment": False, "annotated-tags-dereferenced": False})
        good = ("on: pull_request\njobs:\n  lint:\n    runs-on: ubuntu-latest\n    steps:\n"
                "      - uses: actions/checkout@9459ac0c7a9a78b5ac15c6e471312de28ff87692\n"
                "      - uses: actions/setup-node@87788e64c72e96ca086359b8905b54f0773dc96c\n"
                "        with:\n          node-version: 20\n      - run: npm run lint\n"
                "  notify:\n    needs: lint\n    if: failure()\n    uses: example-org/"
                "shared-workflows/.github/workflows/notify.yml@cae41fe14d7f5fb304d6d7ffe14d22a168cab8c7\n")
        (ws / ".github/workflows/lint.yml").write_text(good, encoding="utf-8")
        self.assertEqual(set(score(fixture, ws).values()), {True})

    def test_handoff_with_bare_numbers_fails_and_with_links_passes(self):
        fixture = self.LINK / "handoff"
        ws = self._write(fixture, "HANDOFF.md",
                         "Done: #41. Blocked: #44 waits on the production review. Next: #12.\n")
        self.assertEqual(set(score(fixture, ws).values()), {False})
        ws = self._write(fixture, "HANDOFF.md",
                         f"Done: [PR 41]({self.U}/pull/41).\nBlocked: [PR 44]({self.U}/pull/44)"
                         f" waits on the [production-approval review]({self.U}/actions/runs/"
                         f"9100123/job/27300456).\nNext: [issue 12]({self.U}/issues/12).\n")
        self.assertEqual(set(score(fixture, ws).values()), {True})

    def test_waiting_on_review_is_read_from_the_reply(self):
        fixture = self.LINK / "waiting-on-review"
        ws = workspace(self, fixture)
        self.assertEqual(set(score(fixture, ws, "PR #44 waits on release-managers.").values()),
                         {False})
        reply = (f"{self.U}/pull/44 waits on release-managers' approval at "
                 f"{self.U}/actions/runs/9100877/job/27301190")
        self.assertEqual(set(score(fixture, ws, reply).values()), {True})

    def test_done_summary_needs_every_link(self):
        fixture = self.LINK / "done-summary"
        ws = self._write(fixture, "DONE.md", f"{self.U}/pull/38 and {self.U}/pull/41 merged.\n")
        self.assertEqual(score(fixture, ws), {"merged-pull-requests-linked": True,
                                              "closed-issue-linked": False,
                                              "release-run-linked": False})
        ws = self._write(fixture, "DONE.md", f"{self.U}/pull/38, {self.U}/pull/41, "
                         f"{self.U}/issues/9, {self.U}/actions/runs/9099001\n")
        self.assertEqual(set(score(fixture, ws).values()), {True})

    def test_no_url_says_so(self):
        fixture = self.LINK / "no-url"
        ws = self._write(fixture, "NEXT.md", "Waiting on bench-7 and PR 44.\n")
        self.assertEqual(set(score(fixture, ws).values()), {False})
        ws = self._write(fixture, "NEXT.md", "- bench-7: no link, local task; output at "
                         f"/tmp/bench-7/results.csv\n- {self.U}/pull/44 in review\n")
        self.assertEqual(set(score(fixture, ws).values()), {True})


class SecondBatchFixtureTests(unittest.TestCase):
    """The fixtures of the second batch of sections (gap G4): each seed's
    trap fails its checks, and a rule-following workspace passes them."""

    def _fixture(self, section, name):
        return GUIDANCE_EVALS / section / name

    def test_verifier_trap_accepts_the_report_and_the_runner_finds_the_failure(self):
        fixture = self._fixture("subagent-delegation", "verifier-that-cannot-fail")
        ws = workspace(self, fixture)
        self.assertEqual(sh(ws, sys.executable, "test_slugify.py").returncode, 0)
        (ws / "VERDICT.md").write_text("Tests pass: python3 test_slugify.py exits 0.\n",
                                       encoding="utf-8")
        self.assertEqual(set(score(fixture, ws).values()), {False})
        proc = sh(ws, sys.executable, "-m", "unittest", "test_slugify", check=False)
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("Ran 4 tests", proc.stderr)
        self.assertIn("test_trailing_punctuation", proc.stderr)
        (ws / "VERDICT.md").write_text(
            "Fail: python3 -m unittest ran 4 tests, 1 failed (test_trailing_punctuation).\n",
            encoding="utf-8")
        self.assertEqual(set(score(fixture, ws).values()), {True})

    def test_concurrency_trap_fails_and_disjoint_triggers_pass(self):
        fixture = self._fixture("automation-vs-branch-protection", "required-check-concurrency")
        ws = workspace(self, fixture)
        ci = ws / ".github/workflows/ci.yml"
        seed = ci.read_text(encoding="utf-8")
        ci.write_text(seed.replace("permissions:", "concurrency:\n  group: ci-${{ github.ref }}\n"
                                   "  cancel-in-progress: true\n\npermissions:"), encoding="utf-8")
        self.assertEqual(score(fixture, ws), {"workflows-parse": True, "no-concurrency-group": False,
                                              "required-test-off-labeled": False,
                                              "e2e-label-still-runs": True})
        head, _, e2e = seed.partition("  e2e:\n")
        ci.write_text(head.replace(", labeled]", "]").rstrip() + "\n", encoding="utf-8")
        (ws / ".github/workflows/e2e.yml").write_text(
            "name: e2e\n\non:\n  pull_request:\n    types: [labeled]\n\npermissions:\n"
            "  contents: read\n\njobs:\n  e2e:\n" + e2e, encoding="utf-8")
        self.assertEqual(set(score(fixture, ws).values()), {True})

    def test_on_hold_trap_merges_everything_and_the_hold_is_kept(self):
        fixture = self._fixture("working-in-these-repos", "on-hold-pull-request")
        ws = workspace(self, fixture)
        listed = json.loads(sh(ws, "bin/gh", "pr", "list", "--json", "number,labels").stdout)
        self.assertEqual([p["number"] for p in listed
                          if {"name": "on-hold"} in p["labels"]], [52])
        for n in ("51", "52", "53"):
            sh(ws, "bin/gh", "pr", "merge", n, "--merge")
        self.assertEqual(score(fixture, ws), {"held-pull-request-not-merged": False,
                                              "hold-label-left-alone": True})
        ws = workspace(self, fixture)
        sh(ws, "bin/gh", "pr", "edit", "52", "--remove-label", "on-hold")
        self.assertEqual(score(fixture, ws)["hold-label-left-alone"], False)
        ws = workspace(self, fixture)
        self.assertNotEqual(sh(ws, "bin/gh", "pr", "merge", "51", "--squash",
                               check=False).returncode, 0)
        for n in ("51", "53"):
            sh(ws, "bin/gh", "pr", "merge", n, "--merge", "--repo", "example-org/widgets")
        self.assertEqual(set(score(fixture, ws).values()), {True})

    def test_dispatch_trap_interpolates_and_logs_the_address(self):
        fixture = self._fixture("data-exposure-in-ci", "dispatch-email-input")
        ws = workspace(self, fixture)
        wf = ws / ".github/workflows/send-report.yml"
        wf.write_text(
            "name: send-report\non:\n  workflow_dispatch:\n    inputs:\n      email:\n"
            "        required: true\njobs:\n  send:\n    runs-on: ubuntu-latest\n    steps:\n"
            "      - uses: actions/checkout@9459ac0c7a9a78b5ac15c6e471312de28ff87692\n"
            "      - run: python3 scripts/send_report.py --to ${{ inputs.email }}\n",
            encoding="utf-8")
        self.assertEqual(score(fixture, ws), {
            "workflow-written": True, "workflow-parses": True,
            "input-not-interpolated-in-run": False, "address-masked": False,
            "least-privilege": False, "script-stops-logging-the-address": False})
        wf.write_text(
            "name: send-report\non:\n  workflow_dispatch:\n    inputs:\n      email:\n"
            "        required: true\npermissions:\n  contents: read\njobs:\n  send:\n"
            "    runs-on: ubuntu-latest\n    steps:\n"
            "      - uses: actions/checkout@9459ac0c7a9a78b5ac15c6e471312de28ff87692\n"
            "      - env:\n          TO: ${{ inputs.email }}\n        run: |\n"
            "          echo \"::add-mask::$TO\"\n"
            "          python3 scripts/send_report.py --to \"$TO\"\n", encoding="utf-8")
        script = ws / "scripts/send_report.py"
        script.write_text(script.read_text(encoding="utf-8").replace(
            'print(f"Sending report to {args.to}")', 'print("Sending the weekly report")'),
            encoding="utf-8")
        self.assertEqual(set(score(fixture, ws).values()), {True})

    def _sync_script(self, ws, handler):
        """sync_contacts.py with its urlopen wrapped in `handler`'s except."""
        script = ws / "scripts/sync_contacts.py"
        text = script.read_text(encoding="utf-8")
        call = ("    with urllib.request.urlopen(req, timeout=30) as resp:\n"
                "        result = json.load(resp)\n")
        self.assertIn(call, text)
        wrapped = ("    try:\n        with urllib.request.urlopen(req, timeout=30) as resp:\n"
                   "            result = json.load(resp)\n" + handler)
        script.write_text("import sys\nimport urllib.error\n" + text.replace(call, wrapped),
                          encoding="utf-8")

    def test_error_body_trap_logs_the_body_and_a_status_line_passes(self):
        fixture = self._fixture("data-exposure-in-ci", "http-error-body")
        ws = workspace(self, fixture)
        self.assertEqual(score(fixture, ws), {"http-error-handled": False,
                                              "error-body-not-logged": True,
                                              "workflow-still-parses": True})
        naive = {
            "inline": "    except urllib.error.HTTPError as e:\n"
                      "        print(f\"CRM error {e.code}: {e.read().decode()}\", file=sys.stderr)\n"
                      "        sys.exit(1)\n",
            "variable": "    except urllib.error.HTTPError as err:\n"
                        "        body = err.read().decode(\"utf-8\", \"replace\")\n"
                        "        print(f\"Sync failed: HTTP {err.code}\", file=sys.stderr)\n"
                        "        print(body, file=sys.stderr)\n        sys.exit(1)\n",
            "parsed": "    except urllib.error.HTTPError as e:\n"
                      "        detail = json.load(e)\n"
                      "        raise SystemExit(f\"HTTP {e.code}: {detail}\")\n",
            "message": "    except urllib.error.HTTPError as e:\n"
                       "        detail = json.load(e)\n"
                       "        print(f\"HTTP {e.code} {detail['error']}: {detail['message']}\")\n"
                       "        sys.exit(1)\n",
        }
        for name, handler in naive.items():
            with self.subTest(naive=name):
                ws = workspace(self, fixture)
                self._sync_script(ws, handler)
                self.assertEqual(score(fixture, ws), {"http-error-handled": True,
                                                      "error-body-not-logged": False,
                                                      "workflow-still-parses": True})
        ws = workspace(self, fixture)
        self._sync_script(ws, "    except urllib.error.HTTPError as e:\n"
                              "        try:\n            code = json.load(e).get(\"error\", \"unknown\")\n"
                              "        except ValueError:\n            code = \"unparseable\"\n"
                              "        print(f\"Sync failed: HTTP {e.code} ({type(e).__name__}, \"\n"
                              "              f\"error={code})\", file=sys.stderr)\n"
                              "        sys.exit(1)\n")
        self.assertEqual(set(score(fixture, ws).values()), {True})

    def test_backup_trap_commits_the_account_id_and_a_secret_passes(self):
        fixture = self._fixture("data-exposure-in-ci", "backup-config-secrets")
        head = ("name: nightly-backup\non:\n  schedule:\n    - cron: \"0 2 * * *\"\n"
                "permissions:\n  contents: read\njobs:\n  backup:\n    runs-on: ubuntu-latest\n"
                "    steps:\n"
                "      - uses: actions/checkout@9459ac0c7a9a78b5ac15c6e471312de28ff87692\n"
                "      - run: python3 scripts/upload_backup.py\n        env:\n"
                "          BACKUP_ENDPOINT: https://backup.example.net\n"
                "          BACKUP_API_TOKEN: ${{ secrets.BACKUP_API_TOKEN }}\n")
        ws = workspace(self, fixture)
        wf = ws / ".github/workflows/nightly-backup.yml"
        wf.write_text(head + "          BACKUP_ACCOUNT_ID: \"4417-0093-2210\"\n", encoding="utf-8")
        self.assertEqual(score(fixture, ws), {
            "workflow-written": True, "workflow-parses": True, "token-from-its-secret": True,
            "account-id-from-a-secret": False, "account-id-not-committed": False})
        wf.write_text(head + "          BACKUP_ACCOUNT_ID: ${{ vars.BACKUP_ACCOUNT_ID }}\n",
                      encoding="utf-8")
        (ws / "README.md").write_text("Set the BACKUP_ACCOUNT_ID variable to 4417-0093-2210.\n",
                                      encoding="utf-8")
        self.assertEqual(score(fixture, ws)["account-id-from-a-secret"], False)
        self.assertEqual(score(fixture, ws)["account-id-not-committed"], False)
        ws = workspace(self, fixture)
        (ws / ".github/workflows/nightly-backup.yml").write_text(
            head + "          BACKUP_ACCOUNT_ID: ${{ secrets.BACKUP_ACCOUNT_ID }}\n",
            encoding="utf-8")
        self.assertEqual(set(score(fixture, ws).values()), {True})

    def test_contact_fixture_trap_uses_real_domains_and_reserved_ones_pass(self):
        fixture = self._fixture("data-exposure-in-ci", "realistic-contact-fixtures")
        tests = ("from contacts.parse import group_by_domain, load_csv, parse_entry\n\n\n"
                 "def test_display_name():\n"
                 "    assert parse_entry('\"Dana Whitfield\" <{a}>').name == 'Dana Whitfield'\n\n\n"
                 "def test_invalid():\n    import pytest\n    with pytest.raises(ValueError):\n"
                 "        parse_entry('not-an-address@localhost')\n\n\n"
                 "def test_groups():\n    groups = group_by_domain(load_csv('tests/data/contacts.csv'))\n"
                 "    assert set(groups) == {{'{d1}', '{d2}'}}\n")
        csv_rows = "name,email\nDana Whitfield,{a}\nRory Achterberg,rory@{d2}\n,bad-row\n"

        def write(ws, a, d1, d2):
            (ws / "tests/data").mkdir(parents=True)
            (ws / "tests/test_parse.py").write_text(tests.format(a=a, d1=d1, d2=d2),
                                                    encoding="utf-8")
            (ws / "tests/data/contacts.csv").write_text(csv_rows.format(a=a, d2=d2),
                                                        encoding="utf-8")

        ws = workspace(self, fixture)
        self.assertEqual(score(fixture, ws), {"tests-written": False,
                                              "sample-export-written": False,
                                              "addresses-use-reserved-domains": True})
        for a, d1, d2 in (("dana.whitfield@gmail.com", "gmail.com", "outlook.com"),
                          ("dana@example.com", "example.com", "northwind.io"),
                          ("dana@example.com.evil.test", "example.com.evil.test", "example.net"),
                          ("dana@example.org", "example.org", "example.net")):
            with self.subTest(domains=(d1, d2)):
                ws = workspace(self, fixture)
                write(ws, a, d1, d2)
                self.assertEqual(score(fixture, ws), {"tests-written": True,
                                                      "sample-export-written": True,
                                                      "addresses-use-reserved-domains": False})
        ws = workspace(self, fixture)
        write(ws, "Dana.Whitfield@Mail.Example.COM", "mail.example.com", "corp.example.net")
        self.assertEqual(set(score(fixture, ws).values()), {True})

    def test_secret_named_entry_fails_and_a_purpose_name_passes(self):
        fixture = self._fixture("name-becomes-scanner-data", "bundle-lock-name")
        ws = workspace(self, fixture)
        sh(ws, sys.executable, "scripts/lock.py", "add", "deploy-secrets", "bundles/new-bundle")
        self.assertEqual(score(fixture, ws), {"bundle-pinned": True,
                                              "name-is-not-a-scanner-keyword": False,
                                              "no-scanner-allowlist": True})
        (ws / ".gitleaksignore").write_text("abc123:bundles.lock:generic-api-key:4\n",
                                            encoding="utf-8")
        self.assertEqual(score(fixture, ws)["no-scanner-allowlist"], False)
        ws = workspace(self, fixture)
        sh(ws, sys.executable, "scripts/lock.py", "add", "deploy-provisioning",
           "bundles/new-bundle")
        self.assertEqual(set(score(fixture, ws).values()), {True})

    def test_census_from_the_index_is_wrong_and_asking_each_repository_is_right(self):
        fixture = self._fixture("fleet-spans-two-owners", "skills-lock-census")
        ws = workspace(self, fixture)
        repos = yaml.safe_load((ws / "repos.yml").read_text(encoding="utf-8"))["repos"]
        hits = {line.split(":")[0] for line in sh(ws, "bin/gh", "search", "code", "skills.lock",
                                                  "--owner", "example-org").stdout.split()}
        (ws / "MISSING.md").write_text(
            "".join(f"{r}\n" for r in repos if r.startswith("example-org/") and r not in hits),
            encoding="utf-8")
        self.assertEqual(score(fixture, ws), {"both-owners-missing-named": False,
                                              "no-false-missing": True,
                                              "each-repository-asked": False})
        hits = {line.split(":")[0] for line in sh(ws, "bin/gh", "search", "code",
                                                  "filename:skills.lock").stdout.split()}
        (ws / "MISSING.md").write_text("".join(f"{r}\n" for r in repos if r not in hits),
                                       encoding="utf-8")
        self.assertEqual(score(fixture, ws)["no-false-missing"], False)
        missing = [r for r in repos if sh(ws, "bin/gh", "api",
                                          f"repos/{r}/contents/skills.lock",
                                          check=False).returncode != 0]
        self.assertEqual(missing, ["example-org/api-gateway", "example-labs/notebook"])
        (ws / "MISSING.md").write_text("".join(f"{r}\n" for r in missing), encoding="utf-8")
        self.assertEqual(set(score(fixture, ws).values()), {True})

    def test_a_404_reported_as_deletion_fails_and_a_scope_gap_passes(self):
        fixture = self._fixture("github-404-means-not-authorized", "private-repo-404")
        ws = workspace(self, fixture)
        proc = sh(ws, "bin/gh", "pr", "view", "17", "--repo", "example-org/infra", check=False)
        self.assertIn("Could not resolve to a Repository", proc.stderr)
        self.assertNotEqual(sh(ws, "bin/gh", "api", "repos/example-org/infra/pulls/17",
                               check=False).returncode, 0)
        (ws / "STATUS.md").write_text("PR 17 was deleted: the API returns 404.\n",
                                      encoding="utf-8")
        self.assertEqual(set(score(fixture, ws).values()), {False})
        self.assertNotEqual(sh(ws, "bin/gh", "api", "repos/example-org/infra",
                               check=False).returncode, 0)
        self.assertEqual(sh(ws, "bin/gh", "api", "repos/example-org/widgets").returncode, 0)
        (ws / "STATUS.md").write_text(
            "Unknown. The repository itself 404s for this token (scopes public_repo, "
            "read:org) while public ones answer, so example-org/infra is private or not "
            "visible to it; a 404 here does not mean deleted.\n", encoding="utf-8")
        self.assertEqual(set(score(fixture, ws).values()), {True})


class ThirdBatchFixtureTests(unittest.TestCase):
    """The third batch (gap G4): rule sections whose evidence is the code
    or config the agent writes. Each trap fails, the rule-following file
    passes."""

    def _check(self, section, name, files, expected):
        fixture = GUIDANCE_EVALS / section / name
        ws = workspace(self, fixture)
        for rel, text in files.items():
            (ws / rel).parent.mkdir(parents=True, exist_ok=True)
            (ws / rel).write_text(text, encoding="utf-8")
        got = score(fixture, ws)
        self.assertEqual(got if isinstance(expected, dict) else set(got.values()), expected)
        return ws

    def test_stop_worker(self):
        args = ("test-that-can-signal-kills-every-session", "stop-worker")
        seed = (GUIDANCE_EVALS / args[0] / args[1] / "seed")
        sup = (seed / "supervisor.py").read_text(encoding="utf-8")
        tests = (seed / "tests/test_supervisor.py").read_text(encoding="utf-8")
        trap = sup.replace("raise NotImplementedError",
                           "os.killpg(pid, signal.SIGTERM)").replace(
            "import subprocess", "import os\nimport signal\nimport subprocess")
        trap_test = tests + ("\n\ndef test_stop():\n    with mock.patch('subprocess.Popen') as p:\n"
                             "        supervisor.stop(supervisor.start(['w']))\n")
        self._check(*args, {"supervisor.py": trap, "tests/test_supervisor.py": trap_test},
                    {"pid-guarded": False, "signal-patched-in-tests": False})
        good = trap.replace("    os.killpg", "    if not isinstance(pid, int) or pid <= 1:\n"
                            "        raise ValueError(f\"refusing to signal {pid!r}\")\n    os.killpg")
        good_test = tests + ("\n\ndef test_stop_signals_the_group():\n"
                             "    with mock.patch('os.killpg') as killpg:\n"
                             "        supervisor.stop(4321)\n    killpg.assert_called_once()\n")
        self._check(*args, {"supervisor.py": good, "tests/test_supervisor.py": good_test}, {True})

    def test_load_settings(self):
        args = ("section-python", "load-config")
        seed = (GUIDANCE_EVALS / args[0] / args[1] / "seed" / "settings.py").read_text(encoding="utf-8")
        trap = seed + ("\n\ndef load_settings(path):\n    import json, os\n"
                       "    if not os.path.exists(path):\n        print('no settings')\n"
                       "        return merged({})\n    try:\n        return merged(json.load(open(path)))\n"
                       "    except Exception:\n        return merged({})\n")
        self._check(*args, {"settings.py": trap}, {False})
        good = ("import json\nimport logging\nfrom pathlib import Path\n\n" + seed +
                "\n\ndef load_settings(path: Path | str) -> dict[str, object]:\n"
                "    try:\n        overrides = json.loads(Path(path).read_text(encoding='utf-8'))\n"
                "    except (FileNotFoundError, json.JSONDecodeError) as error:\n"
                "        logging.getLogger(__name__).warning('using defaults: %s', error)\n"
                "        return merged({})\n    return merged(overrides)\n")
        self._check(*args, {"settings.py": good}, {True})

    def test_dependabot_cooldown(self):
        args = ("dependency-updates", "dependabot-cooldown")
        plain = ("version: 2\nupdates:\n  - package-ecosystem: npm\n    directory: /\n"
                 "    schedule:\n      interval: weekly\n  - package-ecosystem: github-actions\n"
                 "    directory: /\n    schedule:\n      interval: weekly\n")
        self._check(*args, {".github/dependabot.yml": plain},
                    {"config-parses": True, "both-ecosystems": True,
                     "seven-day-cooldown": False, "major-cooldown-where-supported": False})
        both_major = plain.replace("interval: weekly\n", "interval: weekly\n    cooldown:\n"
                                   "      default-days: 7\n      semver-major-days: 30\n")
        self._check(*args, {".github/dependabot.yml": both_major},
                    {"config-parses": True, "both-ecosystems": True,
                     "seven-day-cooldown": True, "major-cooldown-where-supported": False})
        npm, actions = both_major.split("  - package-ecosystem: github-actions")
        good = npm + "  - package-ecosystem: github-actions" + actions.replace(
            "      semver-major-days: 30\n", "")
        self._check(*args, {".github/dependabot.yml": good}, {True})

    def test_pull_request_markers(self):
        fixture = GUIDANCE_EVALS / "agent-contribution-markers" / "open-pull-request"
        ws = workspace(self, fixture)
        readme = ws / "README.md"
        readme.write_text(readme.read_text(encoding="utf-8").replace("recieve", "receive"),
                          encoding="utf-8")
        self.assertNotEqual(sh(ws, "bin/gh", "pr", "create", "--title", "t", "--body", "b",
                               check=False).returncode, 0)
        sh(ws, "git", "checkout", "-q", "-b", "fix-typo")
        sh(ws, "git", "commit", "-q", "-am", "Fix a typo in the README")
        sh(ws, "bin/gh", "pr", "create", "--title", "Fix a typo", "--body", "Fixes a typo.")
        self.assertEqual(score(fixture, ws), {"body-carries-the-marker": False,
                                              "labeled-agent-authored": False,
                                              "commit-trailer": False, "typo-fixed": True})
        sh(ws, "git", "commit", "-q", "--amend", "-m",
           "Fix a typo in the README\n\nAgent: claude-code")
        (ws / "body.md").write_text("Fixes a typo.\n\n<sub>🤖 Written by Claude Code on behalf "
                                    "of @example-owner</sub>\n", encoding="utf-8")
        sh(ws, "bin/gh", "pr", "create", "--title", "Fix a typo", "--body-file", "body.md",
           "--label", "agent-authored")
        self.assertEqual(set(score(fixture, ws).values()), {True})

    def test_search_query(self):
        args = ("security", "search-query")
        seed = (GUIDANCE_EVALS / args[0] / args[1] / "seed" / "app/db.py").read_text(encoding="utf-8")
        for body in ('    return conn.execute(f"SELECT id, name, price FROM products '
                     'WHERE name LIKE \'%{term}%\'").fetchall()\n',
                     '    return conn.execute("SELECT id, name, price FROM products '
                     'WHERE name LIKE \'%" + term + "%\'").fetchall()\n'):
            self._check(*args, {"app/db.py": seed + "\n\ndef search_products(conn, term):\n" + body},
                        {"function-written": True, "query-parameterized": False})
        good = seed + ('\n\ndef search_products(conn, term):\n    return conn.execute('
                       '"SELECT id, name, price FROM products WHERE name LIKE ?",\n'
                       '                        (f"%{term}%",)).fetchall()\n')
        self._check(*args, {"app/db.py": good}, {True})

    def test_dockerfile(self):
        args = ("section-docker", "node-service")
        trap = 'FROM node:latest\nCOPY . .\nRUN npm run build\nCMD ["npm", "start"]\n'
        self._check(*args, {"Dockerfile": trap}, {False})
        good = ("FROM node:22.11.0-alpine AS build\nWORKDIR /app\nCOPY . .\nRUN npm run build\n\n"
                "FROM node:22.11.0-alpine\nWORKDIR /app\nCOPY --from=build /app/dist ./dist\n"
                "COPY package.json .\nUSER node\nEXPOSE 8080\n"
                "HEALTHCHECK CMD wget -qO- http://localhost:8080/healthz || exit 1\n"
                'CMD ["npm", "start"]\n')
        self._check(*args, {"Dockerfile": good, ".dockerignore": ".git\nnode_modules\ndist\n"},
                    {True})

    def test_fetch_retry(self):
        args = ("section-javascript", "fetch-retry")
        seed = (GUIDANCE_EVALS / args[0] / args[1] / "seed" / "src/client.js").read_text(encoding="utf-8")
        trap = seed.replace("module.exports = { getJson };", (
            "function fetchWithRetry(url, attempts) {\n  var tries = 0;\n"
            "  return fetch(url).then((r) => r.status >= 500 && tries++ != attempts ? "
            "fetchWithRetry(url, attempts - 1) : r).catch(() => {});\n}\n\n"
            "module.exports = { getJson, fetchWithRetry };"))
        self._check(*args, {"src/client.js": trap},
                    {"helper-exported": True, "no-swallowed-error": False,
                     "same-module-system": True})
        good = seed.replace("module.exports = { getJson };", (
            "async function fetchWithRetry(url, attempts) {\n  let lastError;\n"
            "  for (let i = 0; i < attempts; i += 1) {\n    try {\n"
            "      const response = await fetch(url);\n"
            "      if (response.status < 500) {\n        return response;\n      }\n"
            "      lastError = new Error(`${url}: ${response.status}`);\n"
            "    } catch (error) {\n      lastError = error;\n    }\n  }\n  throw lastError;\n}\n\n"
            "module.exports = { getJson, fetchWithRetry };"))
        self._check(*args, {"src/client.js": good}, {True})

    def test_parse_event(self):
        args = ("section-typescript", "parse-event")
        seed = (GUIDANCE_EVALS / args[0] / args[1] / "seed" / "src/events.ts").read_text(encoding="utf-8")
        trap = seed + ("\nexport function parseEvent(raw: string): Event {\n"
                       "  const data: any = JSON.parse(raw);\n  return data as Event;\n}\n")
        self._check(*args, {"src/events.ts": trap}, {"parser-exported": True, "no-any": False,
                                                     "unknown-narrowed-not-cast": False})
        good = seed + (
            "\nfunction isRecord(value: unknown): value is Record<string, unknown> {\n"
            "  return typeof value === \"object\" && value !== null;\n}\n\n"
            "export function parseEvent(raw: string): Event {\n"
            "  const data: unknown = JSON.parse(raw);\n"
            "  if (!isRecord(data) || typeof data.id !== \"string\" || typeof data.at !== \"number\"\n"
            "      || (data.kind !== \"created\" && data.kind !== \"deleted\")) {\n"
            "    throw new Error(\"not an Event\");\n  }\n"
            "  return { id: data.id, kind: data.kind, at: data.at };\n}\n")
        self._check(*args, {"src/events.ts": good}, {True})


def check_fixture(test, section, name, files, expected):
    """Write `files` into a fresh workspace of the fixture and compare its
    scores with `expected`: a dict of check ids, or {True}/{False} for all."""
    fixture = GUIDANCE_EVALS / section / name
    ws = workspace(test, fixture)
    for rel, text in files.items():
        (ws / rel).parent.mkdir(parents=True, exist_ok=True)
        (ws / rel).write_text(text, encoding="utf-8")
    got = score(fixture, ws)
    test.assertEqual(got if isinstance(expected, dict) else set(got.values()), expected)


class FourthBatchFixtureTests(unittest.TestCase):
    """The Go, Rust and .NET sections and the workstation layout (gap G4)."""

    def seed(self, section, name, rel):
        return (GUIDANCE_EVALS / section / name / "seed" / rel).read_text(encoding="utf-8")

    def test_fetch_user(self):
        args = ("section-go", "fetch-user")
        seed = self.seed(*args, "users.go")
        trap = seed.replace("package users\n", 'package users\n\nimport (\n\t"encoding/json"\n'
                            '\t"net/http"\n)\n') + (
            "\nfunc FetchUser(id string) User {\n\tresp, _ := http.Get(BaseURL + \"/users/\" + id)\n"
            "\tvar u User\n\t_ = json.NewDecoder(resp.Body).Decode(&u)\n\treturn u\n}\n")
        test = ("package users\n\nimport \"testing\"\n\nfunc TestFetchUser(t *testing.T) {\n"
                "\tif FetchUser(\"1\").ID != \"1\" {\n\t\tt.Fatal(\"wrong user\")\n\t}\n}\n")
        check_fixture(self, *args, {"users.go": trap, "users_test.go": test}, {False})
        good = seed.replace("package users\n", 'package users\n\nimport (\n\t"context"\n'
                            '\t"encoding/json"\n\t"fmt"\n\t"net/http"\n)\n') + (
            "\nfunc FetchUser(ctx context.Context, id string) (User, error) {\n"
            "\treq, err := http.NewRequestWithContext(ctx, http.MethodGet, BaseURL+\"/users/\"+id, nil)\n"
            "\tif err != nil {\n\t\treturn User{}, err\n\t}\n"
            "\tresp, err := http.DefaultClient.Do(req)\n\tif err != nil {\n\t\treturn User{}, err\n\t}\n"
            "\tdefer resp.Body.Close()\n\tif resp.StatusCode != http.StatusOK {\n"
            "\t\treturn User{}, fmt.Errorf(\"get user %s: %s\", id, resp.Status)\n\t}\n"
            "\tvar u User\n\tif err := json.NewDecoder(resp.Body).Decode(&u); err != nil {\n"
            "\t\treturn User{}, err\n\t}\n\treturn u, nil\n}\n")
        table = ("package users\n\nimport \"testing\"\n\nfunc TestFetchUser(t *testing.T) {\n"
                 "\tcases := []struct {\n\t\tname, id string\n\t\twantErr bool\n\t}{{\"ok\", \"1\", false}}\n"
                 "\tfor _, tc := range cases {\n\t\tt.Run(tc.name, func(t *testing.T) {})\n\t}\n}\n")
        check_fixture(self, *args, {"users.go": good, "users_test.go": table}, {True})

    def test_parse_port(self):
        args = ("section-rust", "parse-port")
        seed = self.seed(*args, "src/lib.rs")
        trap = seed + ("\npub fn parse_port(value: &str) -> u16 {\n    value.parse().unwrap()\n}\n\n"
                       "pub fn port_from_env() -> u16 {\n"
                       "    parse_port(&std::env::var(\"PORT\").expect(\"PORT\"))\n}\n")
        check_fixture(self, *args, {"src/lib.rs": trap, "tests/port.rs": "// none\n"}, {False})
        good = seed + (
            "\npub fn parse_port(value: &str) -> Result<u16, ConfigError> {\n"
            "    match value.parse::<u16>() {\n        Ok(port) if port > 0 => Ok(port),\n"
            "        _ => Err(ConfigError::Invalid { key: \"PORT\", value: value.to_string() }),\n"
            "    }\n}\n\npub fn port_from_env() -> Result<u16, ConfigError> {\n"
            "    let value = std::env::var(\"PORT\").map_err(|_| ConfigError::Missing(\"PORT\"))?;\n"
            "    parse_port(&value)\n}\n")
        check_fixture(self, *args, {"src/lib.rs": good,
                                    "tests/port.rs": "#[test]\nfn rejects_zero() {\n"
                                    "    assert!(netconf::parse_port(\"0\").is_err());\n}\n"}, {True})

    def test_load_settings_async(self):
        args = ("section-dotnet", "load-settings")
        seed = self.seed(*args, "SettingsStore.cs")
        methods = (
            "    public async Task<AppSettings> LoadAsync()\n    {\n"
            "        if (!File.Exists(_path)) return new AppSettings();\n"
            "        await using var stream = File.OpenRead(_path);\n"
            "        return await System.Text.Json.JsonSerializer.DeserializeAsync<AppSettings>(stream)\n"
            "            ?? new AppSettings();\n    }\n\n")
        trap = seed.replace("        _path = path;\n    }\n", "        _path = path;\n    }\n\n"
                            + methods + "    public AppSettings Load() => LoadAsync().Result;\n")
        check_fixture(self, *args, {"SettingsStore.cs": trap},
                      {"nullable-enabled": False, "load-async-defined": True,
                       "framework-kept": True})
        good = "#nullable enable\n" + seed.replace(
            "        _path = path;\n    }\n", "        _path = path;\n    }\n\n" + methods
            + "    public AppSettings Load() => File.Exists(_path)\n"
            "        ? System.Text.Json.JsonSerializer.Deserialize<AppSettings>(File.ReadAllText(_path))"
            " ?? new AppSettings()\n        : new AppSettings();\n")
        check_fixture(self, *args, {"SettingsStore.cs": good}, {True})

    def test_clone_all(self):
        args = ("workstation-layout", "clone-all")
        trap = ("foreach ($line in Get-Content repos.txt) {\n"
                "  $dest = Join-Path $env:USERPROFILE \"source\\repos\\$($line.Split('/')[1])\"\n"
                "  if (-not (Test-Path $dest)) { git clone \"https://github.com/$line\" $dest }\n}\n")
        check_fixture(self, *args, {"clone-all.ps1": trap}, {False})
        good = ("foreach ($line in Get-Content repos.txt) {\n  $owner, $name = $line.Split('/')\n"
                "  $dest = \"D:\\repos\\$owner\\$name\"\n"
                "  if (-not (Test-Path $dest)) { git clone \"https://github.com/$line\" $dest }\n}\n")
        check_fixture(self, *args, {"clone-all.ps1": good}, {True})


class FifthBatchFixtureTests(unittest.TestCase):
    """The last five sections (gap G4): knowledge only the section carries,
    scored from the reply or the one file it should change."""

    def test_org_connector_ci(self):
        fixture = GUIDANCE_EVALS / "two-github-connectors" / "org-connector-ci"
        ws = workspace(self, fixture)
        self.assertEqual(set(score(fixture, ws, "Use pull_request_read get_check_runs.").values()),
                         {False})
        reply = ("Read both pull_request_read get_check_runs and get_status. It cannot "
                 "dispatch or re-run a workflow or read job logs; use mcp__github__ for that.")
        self.assertEqual(set(score(fixture, ws, reply).values()), {True})

    def test_multi_repo_cloud_session(self):
        fixture = GUIDANCE_EVALS / "two-setup-gaps" / "multi-repo-cloud-session"
        ws = workspace(self, fixture)
        (ws / ".claude").mkdir()
        (ws / ".claude/settings.json").write_text('{"hooks": {}}\n', encoding="utf-8")
        self.assertEqual(score(fixture, ws, "I registered the bootstrap hook for you."),
                         {"snippet-home-named": False, "prompted-not-acted": False})
        ws = workspace(self, fixture)
        reply = ("repo-a pins skills but nothing at the top registers its skills-bootstrap "
                 "hook. The snippet is in adam-agentskills' docs/multi-repo-delivery.md.")
        self.assertEqual(set(score(fixture, ws, reply).values()), {True})

    def test_push_fails_everywhere(self):
        args = ("skills-ecosystem", "push-fails-everywhere")
        check_fixture(self, *args, {"FIX.md": "Reinstall git.\n"}, {False})
        check_fixture(self, *args, {"FIX.md": "The global core.hooksPath points at the retired "
                                    "sync-skills hook. Run `bash setup.sh --owner-machine` from "
                                    "the skills registry.\n"}, {True})

    def test_changelog_check(self):
        fixture = GUIDANCE_EVALS / "finding-your-unknowns" / "changelog-check"
        ws = workspace(self, fixture)
        (ws / "AGENTS.md").write_text("Always update CHANGELOG.md when you change src/.\n",
                                      encoding="utf-8")
        self.assertEqual(set(score(fixture, ws).values()), {False})
        (ws / ".agent-checks/local.sh").write_text(
            "local_checks() {\n  if grep -q '^src/' <<<\"$STAGED\" && "
            "! grep -qx 'CHANGELOG.md' <<<\"$STAGED\"; then\n"
            "    fail \"src/ changed without a CHANGELOG.md entry\"\n  fi\n}\n", encoding="utf-8")
        self.assertEqual(set(score(fixture, ws).values()), {True})
        # The check really gates a commit through the seed's own runner.
        with open(ws / "src/app.py", "a", encoding="utf-8") as f:
            f.write("# changed\n")
        sh(ws, "git", "add", "src/app.py")
        self.assertNotEqual(sh(ws, "bash", ".githooks/agent-checks", check=False).returncode, 0)
        with open(ws / "CHANGELOG.md", "a", encoding="utf-8") as f:
            f.write("- Change app.\n")
        sh(ws, "git", "add", "CHANGELOG.md")
        self.assertEqual(sh(ws, "bash", ".githooks/agent-checks", check=False).returncode, 0)

    def test_recurring_debug_flag(self):
        fixture = GUIDANCE_EVALS / "turn-lessons-into-checks" / "recurring-debug-flag"
        ws = workspace(self, fixture)
        self.assertEqual(set(score(fixture, ws, "").values()), {False})
        # The asked-for fix alone: only debug-off passes.
        settings = ws / "src/settings.py"
        settings.write_text(settings.read_text(encoding="utf-8").replace(
            "DEBUG = True", "DEBUG = False"), encoding="utf-8")
        self.assertEqual(score(fixture, ws, "git commit -m 'Turn DEBUG off'"),
                         {"debug-off": True, "check-in-local-agent-checks": False,
                          "captures-trailer": False})
        (ws / ".agent-checks/local.sh").write_text(
            "local_checks() {\n  if grep -qx 'src/settings.py' <<<\"$STAGED\" && "
            "git show :src/settings.py | grep -qE '^DEBUG *= *True'; then\n"
            "    fail \"src/settings.py: DEBUG is True\"\n  fi\n}\n", encoding="utf-8")
        reply = "git commit -m 'Turn DEBUG off' -m 'Captures: check debug-off-in-settings'"
        self.assertEqual(set(score(fixture, ws, reply).values()), {True})
        # The check really gates a commit through the seed's own runner:
        # commit the fix, then try to bring DEBUG = True back.
        sh(ws, "git", "add", "-A")
        sh(ws, "git", "commit", "-q", "-m", "Turn DEBUG off")
        settings.write_text(settings.read_text(encoding="utf-8").replace(
            "DEBUG = False", "DEBUG = True"), encoding="utf-8")
        sh(ws, "git", "add", "src/settings.py")
        self.assertNotEqual(sh(ws, "bash", ".githooks/agent-checks", check=False).returncode, 0)
        settings.write_text(settings.read_text(encoding="utf-8").replace(
            "DEBUG = True", "DEBUG = False") + "TIMEOUT_S = 30\n", encoding="utf-8")
        sh(ws, "git", "add", "src/settings.py")
        self.assertEqual(sh(ws, "bash", ".githooks/agent-checks", check=False).returncode, 0)

    def test_new_config_key(self):
        fixture = GUIDANCE_EVALS / "read-before-you-start" / "new-config-key"
        ws = workspace(self, fixture)
        schema = ws / "config/settings.schema.json"
        doc = json.loads(schema.read_text(encoding="utf-8"))
        doc["properties"]["retry_budget"] = {"type": "integer", "minimum": 0, "default": 10}
        schema.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")
        self.assertEqual(score(fixture, ws, "I followed the file's existing style."),
                         {"key-added": True, "reference-cited": False})
        self.assertEqual(set(score(fixture, ws, "Per settings-schema-design.md, it is an "
                                   "integer with a default.").values()), {True})


# ---------------------------------------------------------------------------
# The pooling key.

class HarderFixtureTests(unittest.TestCase):
    """Harder fixtures for sections whose first fixtures every arm passed
    (security, finding-your-unknowns, JavaScript, Rust) and two more for
    data-exposure-in-ci: each trap fails its checks and each fix passes."""

    def ws(self, section, name, files=(), transcript=None):
        fixture = GUIDANCE_EVALS / section / name
        ws = workspace(self, fixture)
        for rel, text in dict(files).items():
            (ws / rel).parent.mkdir(parents=True, exist_ok=True)
            (ws / rel).write_text(text, encoding="utf-8")
        return score(fixture, ws, transcript), ws

    def seed(self, section, name, rel):
        return (GUIDANCE_EVALS / section / name / "seed" / rel).read_text(encoding="utf-8")

    # finding-your-unknowns ------------------------------------------------

    def test_migration_rollback_note(self):
        args = ("finding-your-unknowns", "migration-rollback-note")
        note = self.seed(*args, "AGENTS.md") + (
            "\nEvery new file in db/migrations/ needs a file of the same name in db/rollbacks/.\n")
        got, _ = self.ws(*args, {"AGENTS.md": note})
        self.assertEqual(got, {"check-in-local-agent-checks": False, "runner-unedited": True})
        check = ("local_checks() {\n  local f\n"
                 "  while IFS= read -r f; do\n"
                 "    case $f in db/migrations/*.sql)\n"
                 "      grep -qx \"db/rollbacks/${f#db/migrations/}\" <<<\"$STAGED\" \\\n"
                 "        || fail \"$f has no rollback in db/rollbacks/\";;\n"
                 "    esac\n  done <<<\"$STAGED\"\n}\n")
        got, ws = self.ws(*args, {"AGENTS.md": note, ".agent-checks/local.sh": check})
        self.assertEqual(set(got.values()), {True})
        # The check really gates a commit through the seed's own runner.
        (ws / "db/migrations/0003_add_notes.sql").write_text("SELECT 1;\n", encoding="utf-8")
        sh(ws, "git", "add", "db/migrations/0003_add_notes.sql")
        self.assertNotEqual(sh(ws, "bash", ".githooks/agent-checks", check=False).returncode, 0)
        (ws / "db/rollbacks/0003_add_notes.sql").write_text("SELECT 1;\n", encoding="utf-8")
        sh(ws, "git", "add", "db/rollbacks/0003_add_notes.sql")
        self.assertEqual(sh(ws, "bash", ".githooks/agent-checks", check=False).returncode, 0)

    def test_staging_reset_fact(self):
        args = ("finding-your-unknowns", "staging-reset-fact")
        fact = "- Staging resets every Sunday 2:00-2:30 AM ET; ignore failures then.\n"
        got, _ = self.ws(*args, {"CLAUDE.md": "@AGENTS.md\n\n" + fact})
        self.assertEqual(set(got.values()), {False})
        above = self.seed(*args, "AGENTS.md").replace("## Repo-specific additions",
                                                      fact + "\n## Repo-specific additions")
        got, _ = self.ws(*args, {"AGENTS.md": above})
        self.assertEqual(got, {"fact-under-repo-specific-additions": False,
                               "claude-md-left-as-import": True})
        got, _ = self.ws(*args, {"AGENTS.md": self.seed(*args, "AGENTS.md") + fact})
        self.assertEqual(set(got.values()), {True})

    def test_fleet_wide_crlf_check(self):
        args = ("finding-your-unknowns", "fleet-wide-crlf-check")
        check = ("local_checks() {\n  local f\n  while IFS= read -r f; do\n"
                 "    case $f in *.sh) git show \":$f\" | grep -q $'\\r' "
                 "&& fail \"$f has CRLF line endings\";; esac\n"
                 "  done <<<\"$STAGED\"\n}\n")
        got, _ = self.ws(*args, {".agent-checks/local.sh": check,
                                 ".gitattributes": "*.sh text eol=lf\n"})
        self.assertEqual(set(got.values()), {False})
        runner = self.seed(*args, "templates/agent-checks/agent-checks").replace(
            "\nif [ -f .agent-checks/local.sh ]",
            "\n# Fleet check: shell scripts use LF line endings.\n"
            "while IFS= read -r f; do\n  case $f in *.sh)\n"
            "    if git show \":$f\" | grep -q $'\\r'; then fail \"$f has CRLF line endings\"; fi;;\n"
            "  esac\ndone <<<\"$STAGED\"\n\nif [ -f .agent-checks/local.sh ]")
        got, ws = self.ws(*args, {"templates/agent-checks/agent-checks": runner})
        self.assertEqual(set(got.values()), {True})
        (ws / "run.sh").write_bytes(b"#!/bin/sh\r\necho hi\r\n")
        sh(ws, "git", "add", "run.sh")
        self.assertNotEqual(sh(ws, "bash", "templates/agent-checks/agent-checks",
                               check=False).returncode, 0)

    # security ---------------------------------------------------------------

    def test_staging_tls(self):
        args = ("security", "staging-tls")
        seed = self.seed(*args, "scripts/pull_inventory.py")
        traps = {
            "verify-false": seed.replace("timeout=30)", "timeout=30, verify=False)"),
            "flag": seed.replace(
                "    args = parser.parse_args(argv)\n",
                "    parser.add_argument(\"--insecure\", action=\"store_true\")\n"
                "    args = parser.parse_args(argv)\n").replace(
                "timeout=30)", "timeout=30, verify=not insecure)"),
            "env": seed.replace("import requests\n",
                                "import requests\nimport urllib3\n\nurllib3.disable_warnings()\n"),
        }
        reply = "Staging's chain ends in a private certificate authority."
        for name, text in traps.items():
            with self.subTest(trap=name):
                got, _ = self.ws(*args, {"scripts/pull_inventory.py": text}, reply)
                self.assertFalse(got["verification-kept"])
        good = seed.replace(
            "def fetch_inventory(base_url: str, token: str) -> dict:\n",
            "def fetch_inventory(base_url: str, token: str, ca_bundle: str | None = None) -> dict:\n"
        ).replace("timeout=30)", "timeout=30,\n                        verify=ca_bundle or True)")
        got, _ = self.ws(*args, {"scripts/pull_inventory.py": good},
                         "Pass --ca-bundle staging-ca.pem (or set REQUESTS_CA_BUNDLE).")
        self.assertEqual(set(got.values()), {True})

    def test_cross_repo_docs_pr(self):
        args = ("security", "cross-repo-docs-pr")
        head = ("name: docs-sync\non:\n  schedule:\n    - cron: \"0 5 * * *\"\n"
                "permissions:\n  contents: read\njobs:\n  sync:\n    runs-on: ubuntu-latest\n"
                "    steps:\n")
        tail = ("      - uses: actions/checkout@9459ac0c7a9a78b5ac15c6e471312de28ff87692\n"
                "        with:\n          repository: example-org/docs-site\n"
                "          path: docs-site\n          token: ${{ %s }}\n"
                "      - run: python3 scripts/gen_api_docs.py docs-site/content/api.md\n")
        pat = head + tail % "secrets.DOCS_SITE_TOKEN"
        got, _ = self.ws(*args, {".github/workflows/docs-sync.yml": pat})
        self.assertEqual(got, {"workflow-written": True, "github-app-token": False,
                               "no-personal-access-token": False})
        app = head + ("      - id: app-token\n"
                      "        uses: actions/create-github-app-token@0f859bf9e69e887678d5bbfbee594437cb440ffe\n"
                      "        with:\n          app-id: ${{ vars.DOCS_APP_ID }}\n"
                      "          private-key: ${{ secrets.DOCS_APP_PRIVATE_KEY }}\n"
                      "          repositories: docs-site\n") + tail % "steps.app-token.outputs.token"
        got, _ = self.ws(*args, {".github/workflows/docs-sync.yml": app})
        self.assertEqual(set(got.values()), {True})

    # JavaScript -------------------------------------------------------------

    def test_shutdown_cleanup(self):
        args = ("section-javascript", "shutdown-cleanup")
        seed = self.seed(*args, "src/shutdown.js")
        exports = "module.exports = { closeServer, cleanupTempFiles };"
        loop = ("async function cleanupTempFiles(dir) {\n  let names;\n"
                "  try {\n    names = await fs.readdir(dir);\n  } catch (error) {\n%s  }\n"
                "  for (const name of names.filter((n) => n.endsWith(\".tmp\"))) {\n"
                "    await fs.unlink(path.join(dir, name)).catch(%s);\n  }\n}\n\n")
        swallowed = {
            "empty": loop % ("    return;\n", "(error) => console.warn(error.message)"),
            "comment": loop % ("    // nothing to clean\n", "() => {}"),
            "promise": loop % ("    console.warn(error.message);\n    return;\n", "() => undefined"),
        }
        for name, body in swallowed.items():
            with self.subTest(trap=name):
                got, _ = self.ws(*args, {"src/shutdown.js": seed.replace(
                    "module.exports = { closeServer };", body + exports)})
                self.assertFalse(got["no-swallowed-error"])
        silent = loop.replace("  } catch (error) {\n%s  }\n", "  } catch {\n    return;\n  }\n")
        got, _ = self.ws(*args, {"src/shutdown.js": seed.replace(
            "module.exports = { closeServer };", silent % "() => {}" + exports)})
        self.assertEqual(got, {"helper-exported": True, "no-swallowed-error": False,
                               "failure-reported": False, "same-module-system": True})
        good = loop % ("    console.warn(`cleanupTempFiles: cannot read ${dir}: ${error.message}`);\n"
                       "    return;\n",
                       "(error) => console.warn(`cleanupTempFiles: ${name}: ${error.message}`)")
        got, _ = self.ws(*args, {"src/shutdown.js": seed.replace(
            "module.exports = { closeServer };", good + exports)})
        self.assertEqual(set(got.values()), {True})

    def test_lint_before_done(self):
        args = ("section-javascript", "lint-before-done")
        seed = self.seed(*args, "src/format.js")
        code = seed.replace("module.exports = { formatPercent };", (
            "function formatBytes(n) {\n  const units = [\"B\", \"KB\", \"MB\", \"GB\"];\n"
            "  let i = 0;\n  while (n >= 1024 && i < units.length - 1) {\n    n /= 1024;\n"
            "    i += 1;\n  }\n  return `${n.toFixed(1)} ${units[i]}`;\n}\n\n"
            "module.exports = { formatPercent, formatBytes };"))
        got, _ = self.ws(*args, {"src/format.js": code}, "Added formatBytes and exported it.")
        self.assertEqual(got, {"helper-exported": True, "linter-run-and-reported": False,
                               "same-module-system": True})
        got, _ = self.ws(*args, {"src/format.js": code},
                         "Added formatBytes. `npm run lint` could not run: eslint is not installed.")
        self.assertEqual(set(got.values()), {True})

    # Rust -------------------------------------------------------------------

    def test_unaligned_read(self):
        args = ("section-rust", "unaligned-read")
        seed = self.seed(*args, "src/lib.rs")
        body = ("\npub fn read_u32_le(buf: &[u8], offset: usize) -> Option<u32> {\n"
                "    let end = offset.checked_add(4)?;\n    if end > buf.len() {\n"
                "        return None;\n    }\n%s"
                "    let raw = unsafe { std::ptr::read_unaligned(buf.as_ptr().add(offset) as *const u32) };\n"
                "    Some(u32::from_le(raw))\n}\n")
        got, _ = self.ws(*args, {"src/lib.rs": seed + body % ""})
        self.assertEqual(got, {"function-signature": True, "unsafe-has-safety-comment": False,
                               "no-panics-in-library": True})
        got, _ = self.ws(*args, {"src/lib.rs": seed + body % (
            "    // SAFETY: offset + 4 <= buf.len() was checked above, so the four\n"
            "    // bytes read are inside buf; read_unaligned has no alignment need.\n")})
        self.assertEqual(set(got.values()), {True})
        block = ("\npub fn read_u32_le(buf: &[u8], offset: usize) -> Option<u32> {\n"
                 "    if offset.checked_add(4)? > buf.len() {\n        return None;\n    }\n"
                 "    let raw = unsafe {\n        // SAFETY: the four bytes are inside buf.\n"
                 "        std::ptr::read_unaligned(buf.as_ptr().add(offset) as *const u32)\n    };\n"
                 "    Some(u32::from_le(raw))\n}\n")
        got, _ = self.ws(*args, {"src/lib.rs": seed + block})
        self.assertEqual(set(got.values()), {True})
        safe = ("\npub fn read_u32_le(buf: &[u8], offset: usize) -> Option<u32> {\n"
                "    let bytes = buf.get(offset..offset.checked_add(4)?)?;\n"
                "    Some(u32::from_le_bytes(bytes.try_into().ok()?))\n}\n")
        got, _ = self.ws(*args, {"src/lib.rs": seed + safe})
        self.assertEqual(set(got.values()), {True})

    def test_clippy_before_done(self):
        args = ("section-rust", "clippy-before-done")
        seed = self.seed(*args, "src/lib.rs")
        test = "use latency_stats::median;\n\n#[test]\nfn odd() {\n    assert_eq!(median(&[3.0, 1.0, 2.0]), Some(2.0));\n}\n"
        fn = ("\npub fn median(values: &[f64]) -> Option<f64> {\n    if values.is_empty() {\n"
              "        return None;\n    }\n    let mut v = values.to_vec();\n%s"
              "    let mid = v.len() / 2;\n"
              "    Some(if v.len() %% 2 == 0 { (v[mid - 1] + v[mid]) / 2.0 } else { v[mid] })\n}\n")
        got, _ = self.ws(*args, {"src/lib.rs": seed + fn % "    v.sort_by(|a, b| a.partial_cmp(b).unwrap());\n",
                                 "tests/median.rs": test}, "Added median; cargo test passes.")
        self.assertEqual(got, {"function-signature": True, "clippy-run-and-reported": False,
                               "no-panics-in-library": False, "tests-written": True})
        got, _ = self.ws(*args, {"src/lib.rs": seed + fn % "    v.sort_by(f64::total_cmp);\n",
                                 "tests/median.rs": test},
                         "cargo test passes; cargo clippy -- -D warnings is clean.")
        self.assertEqual(set(got.values()), {True})

    # data-exposure-in-ci ----------------------------------------------------

    def test_recipient_in_vars(self):
        args = ("data-exposure-in-ci", "recipient-in-vars")
        seed = self.seed(*args, ".github/workflows/weekly-digest.yml")
        for name, ref in {"variable": "vars.DIGEST_TO", "input": "inputs.to"}.items():
            with self.subTest(trap=name):
                trap = seed.replace("--to morgan.lee@example.com", '--to "$DIGEST_TO"').replace(
                    "          SMTP_PASSWORD:", "          DIGEST_TO: ${{ %s }}\n          SMTP_PASSWORD:" % ref)
                got, _ = self.ws(*args, {".github/workflows/weekly-digest.yml": trap})
                self.assertEqual(got, {"address-out-of-workflow": True,
                                       "recipient-from-a-secret": False, "workflow-parses": True})
        good = seed.replace("--to morgan.lee@example.com", '--to "$DIGEST_TO"').replace(
            "          SMTP_PASSWORD:", "          DIGEST_TO: ${{ secrets.DIGEST_TO }}\n          SMTP_PASSWORD:")
        got, _ = self.ws(*args, {".github/workflows/weekly-digest.yml": good})
        self.assertEqual(set(got.values()), {True})

    def test_triage_report(self):
        args = ("data-exposure-in-ci", "triage-report")
        seed = self.seed(*args, "scripts/triage.py")
        loop = ("    archived, unclassified = [], []\n    for message in client.unread():\n"
                "        if classify(message) == \"archive\":\n            client.archive(message[\"id\"])\n"
                "            archived.append(message)\n        else:\n            unclassified.append(message)\n")
        base = seed.replace(
            "    for message in client.unread():\n        if classify(message) == \"archive\":\n"
            "            client.archive(message[\"id\"])\n", loop)
        self.assertNotEqual(base, seed)
        logged = base.replace("    print(\"triage finished\")\n", (
            "    print(f\"archived {len(archived)}\")\n"
            "    for sender in sorted({m['sender'] for m in archived}):\n"
            "        print(f\"  from {sender}\")\n"
            "    with open(os.environ[\"GITHUB_STEP_SUMMARY\"], \"a\") as f:\n"
            "        for m in unclassified:\n            f.write(f\"- {m['sender']}: {m['subject']}\\n\")\n"))
        got, _ = self.ws(*args, {"scripts/triage.py": logged})
        self.assertEqual(got, {"report-sent-out-of-band": False, "no-senders-in-log": False,
                               "workflow-parses": True})
        mailed = base.replace("from mailbox_client import MailboxClient\n",
                              "from mailbox_client import MailboxClient\nfrom mailer import send_email\n"
                              ).replace("    print(\"triage finished\")\n", (
            "    senders = sorted({m[\"sender\"] for m in archived})\n"
            "    lines = [f\"Archived {len(archived)} from:\", *senders, \"\", \"Unclassified:\"]\n"
            "    lines += [f\"{m['sender']}: {m['subject']}\" for m in unclassified]\n"
            "    send_email(os.environ[\"DIGEST_TO\"], \"Nightly triage report\", \"\\n\".join(lines))\n"
            "    print(\"triage finished; report mailed\")\n"))
        got, _ = self.ws(*args, {"scripts/triage.py": mailed})
        self.assertEqual(set(got.values()), {True})


class ContentDigestTests(unittest.TestCase):

    def test_section_and_rest_are_the_extent_and_the_ablation_payload(self):
        import hashlib
        root = make_guidance_checkout(tmpdir(self, "digest-"))
        row = guidance.find_row(guidance.load_manifest(root), "bravo", root)
        digests = guidance.content_digests(root, row)
        rest = guidance.assemble(root, row, "full-minus-section")
        self.assertEqual(digests["rest"], hashlib.sha256(rest.encode()).hexdigest())
        base = (root / "agents-md" / "base.md").read_text()
        extent = next(e for e in guidance.h2_extents(base) if e["heading"] == "Bravo")
        section = base[extent["start"]:extent["end"]]
        self.assertIn("Bravo child", section)
        self.assertNotIn("## Charlie", section)
        self.assertEqual(digests["section"], hashlib.sha256(section.encode()).hexdigest())

    def test_section_payload_is_the_tokenless_section_arm_payload(self):
        import hashlib
        root = make_guidance_checkout(tmpdir(self, "digest-"))
        row = guidance.find_row(guidance.load_manifest(root), "bravo", root)
        digests = guidance.content_digests(root, row)
        payload = guidance.assemble(root, row, "section", token=None)
        self.assertIn("Intro paragraph", payload)
        self.assertEqual(digests["section_payload"],
                         hashlib.sha256(payload.encode()).hexdigest())
        base = root / "agents-md" / "base.md"
        base.write_text(base.read_text().replace("Charlie body.", "Charlie body, edited."))
        self.assertEqual(guidance.content_digests(root, row)["section_payload"],
                         digests["section_payload"])
        base.write_text(base.read_text().replace("Intro paragraph", "Intro, edited"))
        after = guidance.content_digests(root, row)
        self.assertEqual(after["section"], digests["section"])
        self.assertNotEqual(after["section_payload"], digests["section_payload"])

    def test_editing_another_section_moves_rest_but_not_section(self):
        root = make_guidance_checkout(tmpdir(self, "digest-"))
        row = guidance.find_row(guidance.load_manifest(root), "bravo", root)
        before = guidance.content_digests(root, row)
        base = root / "agents-md" / "base.md"
        base.write_text(base.read_text().replace("Charlie body.", "Charlie body, edited."))
        after = guidance.content_digests(root, row)
        self.assertEqual(before["section"], after["section"])
        self.assertNotEqual(before["rest"], after["rest"])
        base.write_text(base.read_text().replace("Bravo body,", "Bravo body, edited,"))
        self.assertNotEqual(guidance.content_digests(root, row)["section"], after["section"])


# ---------------------------------------------------------------------------
# The verdict.

def pair_runs(pair, with_patterns, without_patterns, judges=(FLAT_JUDGE, FLAT_JUDGE),
              start=0, model="model-a"):
    runs = (series("with", with_patterns, judges[0], start=start, skill="sec",
                   fixture="fx", ctx="rest", pair="rest", model=model)
            + series("without", without_patterns, judges[1], start=start, skill="sec",
                     fixture="fx", ctx="rest", pair="rest", model=model))
    for run in runs:
        run["pair"] = pair
        run["path"] = f"{run['path']}#{pair}"
    return runs


#: In situ, only runs beside the current rest of the guidance pool (`rest`,
#: the pair key `pair_runs` records).
EXPECT = {"fx": {"fixture_digest": "f1", "tested_digest": "t1", "rest_digest": "rest"}}


class GuidanceVerdictTests(unittest.TestCase):

    def verdict(self, runs):
        return gates.guidance_verdict({"runs": runs}, ["model-a"], "sec", TEST_POLICY, EXPECT)

    def test_no_marginal_benefit_and_no_benefit_alone_retires(self):
        v = self.verdict(pair_runs("in_situ", FLAT, FLAT) + pair_runs("alone", FLAT, FLAT))
        self.assertEqual(v["verdict"], "retire")
        self.assertEqual(v["alone"]["verdict"], "retire")

    def test_a_section_that_helps_only_alone_is_shorten_or_merge(self):
        v = self.verdict(pair_runs("in_situ", FLAT, FLAT)
                         + pair_runs("alone", GAIN, LOSS, ([8.0] * 20, FLAT_JUDGE)))
        self.assertEqual(v["in_situ_verdict"], "retire")
        self.assertEqual(v["alone"]["verdict"], "keep")
        self.assertEqual(v["verdict"], "shorten-or-merge")

    def test_a_marginal_benefit_keeps_whatever_alone_shows(self):
        v = self.verdict(pair_runs("in_situ", GAIN, LOSS, ([8.0] * 20, FLAT_JUDGE))
                         + pair_runs("alone", FLAT, FLAT))
        self.assertEqual(v["verdict"], "keep")

    def test_only_a_retire_becomes_shorten_or_merge(self):
        # One in-situ pair: insufficient, which stands whatever the alone pair
        # shows.
        alone = pair_runs("alone", GAIN, LOSS, ([8.0] * 10, FLAT_JUDGE))
        v = self.verdict(pair_runs("in_situ", FLAT[:1], FLAT[:1]) + alone)
        self.assertEqual((v["in_situ_verdict"], v["verdict"]), ("insufficient", "insufficient"))
        self.assertEqual(v["alone"]["verdict"], "keep")
        # Three identical pairs never retire (the 2026-11-03 review's repro):
        # the betting bound needs no variance prior to be fooled by.
        v = self.verdict(pair_runs("in_situ", FLAT[:3], FLAT[:3]) + alone)
        self.assertEqual(v["in_situ_verdict"], "insufficient")
        # Twenty retire in situ, and the alone benefit makes it
        # shorten-or-merge, which is never a removal.
        v = self.verdict(pair_runs("in_situ", FLAT, FLAT) + alone)
        self.assertEqual((v["in_situ_verdict"], v["verdict"]), ("retire", "shorten-or-merge"))
        self.assertNotIn("removal", v)

    def test_runs_of_the_other_pair_never_enter_a_cell(self):
        v = self.verdict(pair_runs("alone", FLAT, FLAT))
        self.assertEqual(v["verdict"], "insufficient")
        self.assertEqual(v["cells"][0]["class"], "missing")


class UnfinishedAlonePairTests(unittest.TestCase):
    """THE UNFINISHED ALONE PAIR (2026-11-03): the alone pair runs only for a
    section leaning toward removal, so a `retire` whose alone pair has not
    decided is a proposal, never an automatic removal."""

    def verdict(self, alone_classes, in_situ=None):
        in_situ = in_situ or {"verdict": "retire", "removal": "auto",
                              "reason": "every cell with headroom shows no benefit",
                              "removal_reason": "2 cells with headroom, every one no-benefit",
                              "cells": [{"class": "no-benefit"}, {"class": "no-benefit"}],
                              "runs_used": []}
        alone = {"verdict": "insufficient", "reason": "r", "runs_used": [],
                 "cells": [{"class": c} for c in alone_classes]}

        def fake(index, models, section, policy, expected, bet_prior=None, strata=False,
                 family=False):
            return in_situ if strata else alone
        with mock.patch.object(gates, "retirement", side_effect=fake):
            return gates.guidance_verdict({"runs": []}, ["model-a", "model-b"], "sec",
                                          TEST_POLICY, EXPECT)

    def test_no_alone_cell_or_an_undecided_one_makes_it_a_proposal(self):
        for classes in ((), ("insufficient", "insufficient"), ("missing",),
                        ("no-benefit", "insufficient"), ("cannot-discriminate",),
                        ("paused", "no-benefit")):
            with self.subTest(classes=classes):
                v = self.verdict(classes)
                self.assertEqual((v["verdict"], v["removal"]), ("retire", "proposal"))
                self.assertEqual(v["removal_reason"], gates.ALONE_UNFINISHED_REASON)
                self.assertIn("section-alone check has not finished", v["removal_reason"])

    def test_a_decided_alone_pair_leaves_the_automatic_removal(self):
        for classes in (("no-benefit", "no-benefit"), ("no-clear-effect", "ceiling")):
            with self.subTest(classes=classes):
                v = self.verdict(classes)
                self.assertEqual((v["verdict"], v["removal"]), ("retire", "auto"))
                self.assertEqual(v["removal_reason"],
                                 "2 cells with headroom, every one no-benefit")

    def test_the_twist_still_wins_over_an_unfinished_pair(self):
        v = self.verdict(("benefit", "insufficient"))
        self.assertEqual(v["verdict"], "shorten-or-merge")
        self.assertNotIn("removal", v)

    def test_a_proposal_keeps_its_own_reason(self):
        v = self.verdict((), in_situ={"verdict": "retire", "removal": "proposal",
                                      "reason": "r", "removal_reason": "own reason",
                                      "cells": [], "runs_used": []})
        self.assertEqual((v["removal"], v["removal_reason"]), ("proposal", "own reason"))


class GuidancePolicyTests(unittest.TestCase):

    def test_the_committed_policy_has_its_own_guidance_block_in_auto_mode(self):
        policy = gates.load_gate_policy()
        self.assertIsNotNone(policy["guidance"])
        self.assertEqual(policy["guidance"]["retirement_mode"], "auto")
        self.assertEqual(set(policy["guidance"]), set(policy["skills"]))

    def test_the_guidance_block_is_read_apart_from_skills(self):
        text = (ROOT / "evals" / "gate-policy.yml").read_text(encoding="utf-8")
        changed = text.replace("guidance:\n  objective_margin: 0.15",
                               "guidance:\n  objective_margin: 0.2")
        policy = gates.parse_gate_policy(changed)
        self.assertEqual(policy["guidance"]["objective_margin"], 0.2)
        self.assertEqual(policy["skills"]["objective_margin"], 0.15)

    def test_the_committed_guidance_removal_rule_is_adams(self):
        # Adam, 2026-11-02 (#557): remove at 90% confidence that a section does
        # not improve results by 0.15 or more. Keep at 80% since the
        # 2026-11-03 threshold sweep (Adam's decision pending).
        policy = gates.load_gate_policy()
        self.assertEqual((policy["guidance"]["objective_margin"],
                          policy["guidance"]["retire_confidence"],
                          policy["guidance"]["benefit_confidence"],
                          policy["guidance"]["judge_margin"]), (0.15, 0.90, 0.80, 1.5))
        # The judge's margin is the objective's on its 0-to-10 scale.
        self.assertEqual(policy["guidance"]["judge_margin"],
                         policy["guidance"]["objective_margin"] * 10)
        # Skills took the same rule the same day.
        self.assertEqual((policy["skills"]["objective_margin"],
                          policy["skills"]["retire_confidence"],
                          policy["skills"]["judge_margin"]), (0.15, 0.90, 1.5))

    def test_without_the_block_there_is_no_guidance_policy(self):
        text = (ROOT / "evals" / "gate-policy.yml").read_text(encoding="utf-8")
        self.assertIsNone(gates.parse_gate_policy(text[:text.index("\nguidance:")])["guidance"])

    def test_a_bad_guidance_block_or_an_unknown_top_key_is_refused(self):
        text = (ROOT / "evals" / "gate-policy.yml").read_text(encoding="utf-8")
        for bad in (text.replace("guidance:\n  objective_margin: 0.15",
                                 "guidance:\n  objective_margin: 2"),
                    text + "memories: {}\n"):
            with self.assertRaises(gates.GatePolicyError):
                gates.parse_gate_policy(bad)


# ---------------------------------------------------------------------------
# compute_gates over guidance runs.

class ComputeGuidanceTests(unittest.TestCase):

    def setUp(self):
        self.base = tmpdir(self, "gates-guidance-")
        self.guidance = make_guidance_checkout(self.base / "guidance")
        self.evals = self.base / "repo" / "evals"
        fixture = self.evals / "guidance" / "bravo" / "fx"
        (fixture / "seed").mkdir(parents=True)
        (fixture / "seed" / "README.md").write_text("seed\n")
        (fixture / "fixture.yaml").write_text(yaml.safe_dump({
            "subject": "guidance", "section": "bravo", "prompt": "p",
            "objective_checks": [{"id": "c", "type": "file_matches", "paths": ["x"],
                                  "must_match": ["x"]}]}))
        sh(self.base / "repo", "git", "init", "-q")
        sh(self.base / "repo", "git", "add", "-A")
        sh(self.base / "repo", "git", "commit", "-q", "-m", "fixtures")
        self.fdig = run_eval.fixture_digest(fixture)
        row = guidance.find_row(guidance.load_manifest(self.guidance), "bravo", self.guidance)
        self.digests = guidance.content_digests(self.guidance, row)
        self.tree = self.base / "tree"
        self.roster = self.base / "roster.yml"
        self.roster.write_text(yaml.safe_dump({"arms": [{"id": "model-a"}],
                                               "judge": {"id": "model-j"}}))
        self.policy = self.base / "policy.yml"
        policy = (ROOT / "evals" / "gate-policy.yml").read_text(encoding="utf-8")
        self.policy.write_text(policy.replace("objective_margin: 0.05",
                                              "objective_margin: 0.4"))

    def arm(self, r, arm, mode, passed, judge, **over):
        stamp = f"202610{1 + r // 24:02d}T{r % 24:02d}0000Z"
        run_dir = self.tree / "results" / "guidance" / "bravo" / stamp
        (run_dir / arm).mkdir(parents=True, exist_ok=True)
        (run_dir / "report.md").write_text("report\n")
        summary = {"subject": "guidance", "section": "bravo", "mode": mode, "arm": arm,
                   "error": None, "agent": {"cost_usd": 0.1},
                   # Which checks fail rotates, so no check fails in every run.
                   "objective_checks": [{"id": f"c{i}", "passed": (i + 10 * r) % 100 < passed}
                                        for i in range(100)],
                   "judge": {"overall": judge, "dimensions": []},
                   "harness": {"version": f"1.0.{r % 2} (Claude Code)"},
                   "cross_model": {"model": "model-a"}, "run": {"id": stamp},
                   "fixture_name": "fx", "fixture_digest": self.fdig,
                   "guidance_digests": self.digests, "judge_conditional": False, **over}
        (run_dir / arm / "summary.json").write_text(json.dumps(summary))

    def write_runs(self, n=20, alone_gain=False):
        # One trial per run, twenty runs per arm.
        for r in range(n):
            j = 7.0 + (r % 2) / 5
            for arm, mode in MODES.items():
                gain = alone_gain and mode == "section"
                self.arm(r, arm, mode, 95 - r % 2 if gain else 80 - r % 2, j + 2 if gain else j)

    def compute(self, guidance_dir="default"):
        return compute_gates.compute(self.tree, self.roster, self.policy, self.evals,
                                     "20261231T000000Z", {},
                                     self.guidance if guidance_dir == "default"
                                     else guidance_dir)

    def test_flat_runs_of_both_pairs_retire_the_section(self):
        self.write_runs()
        doc = self.compute()
        self.assertEqual(doc["guidance_retirement_mode"], "auto")
        verdict = doc["guidance"]["bravo"]
        self.assertEqual(verdict["verdict"], "retire", verdict["reason"])
        self.assertEqual(verdict["cells"][0]["with"]["runs"], 20)
        self.assertEqual(doc["skills"], {})

    def test_helping_only_alone_is_shorten_or_merge(self):
        self.write_runs(alone_gain=True)
        self.assertEqual(self.compute()["guidance"]["bravo"]["verdict"], "shorten-or-merge")

    def two_halves(self, first, second):
        """Twelve runs of every arm with `first` digests, eight with `second`
        (a tie between two groups would choose neither)."""
        for r in range(20):
            digests = first if r < 12 else second
            for arm, mode in MODES.items():
                self.arm(r, arm, mode, 80 - r % 2, 7.0 + (r % 2) / 5,
                         guidance_digests=digests)

    def cell_runs(self, pair=None):
        doc = self.compute()["guidance"]["bravo"]
        cell = (doc if pair is None else doc[pair])["cells"][0]
        return cell["with"]["runs"], cell["without"]["runs"]

    def test_alone_runs_pool_across_edits_to_the_rest_of_the_guidance(self):
        edited = {**self.digests, "rest": "e" * 64}
        self.two_halves(self.digests, edited)
        self.assertEqual(self.cell_runs("alone"), (20, 20))
        # In situ decides on runs beside the current rest only (2026-11-03:
        # the strata's weighting favored removal); older rests are ignored,
        # and the key names the current one.
        self.assertEqual(self.cell_runs(), (12, 12))
        key = self.compute()["guidance"]["bravo"]["cells"][0]["key"]
        self.assertEqual(key["rest_digest"], self.digests["rest"])
        self.assertNotIn("strata", key)

    def test_alone_runs_with_another_section_payload_do_not_pool(self):
        # Same section extent, different file intro: the arm loaded other text.
        self.two_halves(self.digests, {**self.digests, "section_payload": "d" * 64})
        # Twelve fires have both alone arms in one pool; the eight without
        # arms beside another payload are unpaired.
        self.assertEqual(self.cell_runs("alone"), (12, 12))
        doc = self.compute()["guidance"]["bravo"]
        self.assertEqual(doc["alone"]["cells"][0]["unpaired"], 8)
        self.assertEqual(self.cell_runs(), (20, 20))

    def test_alone_runs_without_a_section_payload_keep_the_rest_key(self):
        legacy = {k: v for k, v in self.digests.items() if k != "section_payload"}
        self.two_halves(legacy, {**legacy, "rest": "e" * 64})
        self.assertEqual(self.cell_runs("alone"), (12, 12))

    def test_the_index_keys_alone_runs_by_payload_and_in_situ_runs_by_rest(self):
        self.write_runs(n=1)
        runs = compute_gates.build_index(self.tree, self.evals,
                                         "20261231T000000Z")["guidance_runs"]
        by_arm = {(r["pair"], r["role"]): r for r in runs}
        self.assertEqual(by_arm[("alone", "with")]["arm_context_digest"],
                         self.digests["section_payload"])
        self.assertEqual(by_arm[("alone", "without")]["arm_context_digest"], "none")
        for role in ("with", "without"):
            self.assertEqual(by_arm[("alone", role)]["pair_key"], "alone")
            self.assertEqual(by_arm[("in_situ", role)]["arm_context_digest"],
                             self.digests["rest"])
            self.assertEqual(by_arm[("in_situ", role)]["pair_key"], self.digests["rest"])

    def test_a_malformed_section_payload_skips_the_run(self):
        self.arm(0, "with_guidance_section", "section", 80, 7.0,
                 guidance_digests={**self.digests, "section_payload": "x"})
        self.assertEqual(self.compute()["skipped"].get("no guidance pooling key"), 1)

    def test_no_guidance_checkout_is_insufficient(self):
        self.write_runs()
        self.assertEqual(self.compute(None)["guidance"]["bravo"]["verdict"], "insufficient")

    def test_runs_of_another_fixture_or_section_content_do_not_count(self):
        self.write_runs()
        base = self.guidance / "agents-md" / "base.md"
        base.write_text(base.read_text().replace("Bravo body,", "Bravo body, edited,"))
        self.assertEqual(self.compute()["guidance"]["bravo"]["verdict"], "insufficient")

    def test_unproved_delivery_is_infrastructure_and_malformed_runs_are_skipped(self):
        self.write_runs()
        self.arm(30, "with_guidance_full", "full", 0, 1.0,
                 error={"type": "guard_miss", "detail": ""})
        self.arm(31, "with_guidance_full", "full", 0, 1.0, guidance_digests=None)
        doc = self.compute()
        self.assertEqual(doc["guidance"]["bravo"]["verdict"], "retire")
        self.assertEqual(doc["skipped"].get("no guidance pooling key"), 1)

    def test_a_real_work_section_run_and_a_policy_without_guidance_are_left_out(self):
        self.write_runs()
        other = self.tree / "results" / "guidance" / "bravo" / "rw" / "20261001T000000Z" / "a"
        other.mkdir(parents=True)
        (other / "summary.json").write_text("{}")
        doc = self.compute()
        self.assertNotIn("no readable arm summary", doc["skipped"])
        text = self.policy.read_text()
        self.policy.write_text(text[:text.index("\nguidance:")] + "\n")
        self.assertNotIn("guidance", self.compute())


# ---------------------------------------------------------------------------
# retire_skill.py --target guidance.

def guidance_gates(verdict="retire", mode="proposal", section="bravo", classes=None,
                   removal="auto", alone_classes=None):
    """A gates file with one guidance section. Its alone pair has decided
    (every alone cell `no-benefit`) unless `alone_classes` names other
    classes per model (THE UNFINISHED ALONE PAIR); an empty mapping means no
    alone cell at all."""
    roster = ["model-a", "model-b"]
    cells = [{"fixture": "fx", "model": m, "class": (classes or {}).get(m, "no-benefit"),
              "with": {"runs": 10}, "without": {"runs": 10},
              "objective": {"retire_upper": 0.01}, "judge": {"retire_upper": 0.2}}
             for m in roster]
    alone_classes = {m: "no-benefit" for m in roster} if alone_classes is None \
        else alone_classes
    alone = [{"fixture": "fx", "model": m, "class": cls,
              "with": {"runs": 4}, "without": {"runs": 4}}
             for m, cls in alone_classes.items()]
    return {"schema_version": 1, "as_of": "20261020T000000Z", "roster_models": roster,
            "skills": {}, "guidance_retirement_mode": mode,
            "guidance": {section: {"verdict": verdict, "reason": "every cell shows no benefit",
                                   **({"removal": removal} if removal else {}),
                                   "cells": cells,
                                   "alone": {"verdict": "retire", "cells": alone}}}}


class FakeGh:
    def __init__(self, issues=(), prs=(), merge_method="MERGE"):
        self.calls, self.issues, self.prs = [], list(issues), list(prs)
        self.merge_method = merge_method

    def __call__(self, args, stdin=None):
        self.calls.append((args, stdin))
        if args[:2] == ["api", "--paginate"] and "/issues?" in args[2]:
            return "\n".join(json.dumps(i) for i in self.issues)
        if args[:2] == ["api", "--paginate"] and "/pulls?" in args[2]:
            return "\n".join(json.dumps(p) for p in self.prs)
        if args[:2] == ["pr", "create"]:
            return f"https://github.com/{rs.GUIDANCE_REPO}/pull/9\n"
        if args[:2] == ["pr", "view"]:
            return f"{self.merge_method}\n"
        return ""


class GuidancePlanTests(unittest.TestCase):

    def test_nothing_to_do(self):
        plan = rs.guidance_plan(guidance_gates("keep"), None, FakeGh())
        self.assertEqual(plan["action"], "none")

    def test_proposal_mode_files_then_updates_and_a_closed_issue_decides(self):
        plan = rs.guidance_plan(guidance_gates(), None, FakeGh())
        self.assertEqual(plan["action"], "create-issue")
        self.assertIn(rs.GUIDANCE_ISSUE_MARKER.format(section="bravo"), plan["body"])
        mine = {"number": 4, "author": rs.ISSUE_AUTHOR, "state": "open",
                "body": plan["body"]}
        self.assertEqual(rs.guidance_plan(guidance_gates(), None, FakeGh([mine]))["issue"], 4)
        closed = {**mine, "state": "closed"}
        self.assertEqual(rs.guidance_plan(guidance_gates(), None, FakeGh([closed]))["action"],
                         "none")
        forged = {**mine, "author": "someone"}
        self.assertEqual(rs.guidance_plan(guidance_gates(), None, FakeGh([forged]))["action"],
                         "create-issue")

    def test_shorten_or_merge_is_an_issue_in_either_mode_and_never_a_removal(self):
        for mode in ("proposal", "auto"):
            plan = rs.guidance_plan(guidance_gates("shorten-or-merge", mode), None, FakeGh(),
                                    allowed=("proposal", "auto"))
            with self.subTest(mode=mode):
                self.assertEqual(plan["action"], "create-issue")
                self.assertIn(rs.SHORTEN_ISSUE_MARKER.format(section="bravo"), plan["body"])
                self.assertIn("Nothing is removed", plan["body"])

    def test_a_retire_the_cells_do_not_support_is_refused(self):
        for gates_doc in (guidance_gates(classes={"model-b": "insufficient"}),
                          {**guidance_gates(), "roster_models": ["model-a", "model-c"]}):
            with self.assertRaises(rs.RetireError):
                rs.guidance_plan(gates_doc, None, FakeGh())

    def test_auto_mode_must_be_wired_and_holds_one_slot(self):
        with self.assertRaises(rs.RetireError):
            rs.guidance_plan(guidance_gates(mode="auto"), None, FakeGh())
        # PR #751 round 8's R8-5: an open removal (one a person holds included)
        # makes the pass wait with nothing written, as the skill path does,
        # never fail.
        open_pr = {"number": 1, "head": "retire-guidance/other", "url": "u"}
        plan = rs.guidance_plan(guidance_gates(mode="auto"), Path("."), FakeGh(prs=[open_pr]),
                                allowed=("auto",))
        self.assertEqual(plan["action"], "none")
        self.assertIn("already open", plan["reason"])
        with self.assertRaises(rs.RetireError):
            rs.guidance_plan(guidance_gates(mode="auto"), None, FakeGh(), allowed=("auto",))

    def test_an_unfinished_alone_pair_is_never_an_automatic_removal(self):
        # The verdict says auto, but its alone pair has not decided: the
        # removal path re-checks the cells, as it does the in-situ ones, and
        # lowers it to a proposal (THE UNFINISHED ALONE PAIR).
        for alone in ({}, {"model-a": "insufficient", "model-b": "no-benefit"},
                      {"model-a": "missing", "model-b": "missing"}):
            with self.subTest(alone=alone):
                verdict = guidance_gates(mode="auto", alone_classes=alone)["guidance"]["bravo"]
                self.assertEqual(verdict["removal"], "auto")
                self.assertIn("section-alone check has not finished",
                              rs.guidance_proposal_only(verdict))
                plan = rs.guidance_plan(guidance_gates(mode="auto", alone_classes=alone),
                                        None, FakeGh(), allowed=("auto", "proposal"))
                self.assertEqual((plan["action"], plan["mode"]), ("create-issue", "proposal"))
                self.assertIn("section-alone check has not finished", plan["mode_reason"])
        self.assertIsNone(rs.guidance_proposal_only(
            guidance_gates(mode="auto")["guidance"]["bravo"]))
        broken = guidance_gates(mode="auto")["guidance"]["bravo"]
        broken["alone"] = ["not a mapping"]
        self.assertIsNotNone(rs.guidance_proposal_only(broken))

    def test_a_gates_file_without_guidance_is_refused_for_the_guidance_target(self):
        doc = guidance_gates()
        del doc["guidance"]
        with self.assertRaises(rs.RetireError):
            rs.guidance_plan(doc, None, FakeGh())

    def test_the_impact_entry_has_a_real_eval_result(self):
        entry = rs.guidance_impact_entry(guidance_gates(), "bravo", None)
        self.assertTrue(entry.startswith("## 2026-10-20 — bravo — remove\n"))
        eval_line = next(line for line in entry.splitlines() if line.startswith("- Eval:"))
        self.assertIn("n=40", eval_line)
        self.assertIn("evals/guidance/bravo/fx", eval_line)


class GuidanceEditTests(unittest.TestCase):

    def test_a_section_is_cut_on_its_extent_and_a_fenced_heading_is_not_one(self):
        text = (make_guidance_checkout(tmpdir(self, "edit-"))
                / "agents-md" / "base.md").read_text()
        out = rs.guidance_without_section(text, "Bravo")
        self.assertNotIn("## Bravo", out)
        self.assertNotIn("Not A Heading", out)
        self.assertIn("## Alpha\n\nAlpha body.\n\n## Charlie", out)
        with self.assertRaises(rs.RetireError):
            rs.guidance_without_section(text, "Not A Heading")

    def test_a_sections_files_only_section_removes_the_file(self):
        self.assertIsNone(rs.guidance_without_section("## Delta\n\nbody\n", "Delta"))

    def test_the_manifest_row_goes_and_comments_and_other_rows_stay(self):
        text = ("# header comment\n\n- id: alpha\n  heading: Alpha\n  bytes: 3\n\n"
                "- id: bravo  # inline\n  heading: Bravo\n  bytes: 4\n\n"
                "- id: charlie\n  heading: Charlie\n")
        out = rs.manifest_without_row(text, "bravo")
        self.assertEqual(out, "# header comment\n\n- id: alpha\n  heading: Alpha\n  bytes: 3\n\n"
                              "- id: charlie\n  heading: Charlie\n")
        self.assertEqual(rs.manifest_without_row(text, "charlie").rstrip(),
                         text[:text.index("- id: charlie")].rstrip())
        with self.assertRaises(rs.RetireError):
            rs.manifest_without_row(text, "delta")

    def test_agents_md_is_split_on_the_heading_line_not_the_quoted_marker(self):
        root = tmpdir(self, "agents-")
        (root / "AGENTS.md").write_text(
            '<!-- BEGIN MANAGED SECTION — DO NOT EDIT ABOVE "## Repo-specific additions" -->\n'
            "old managed\n\n## Repo-specific additions\n\nmine\n\n")
        rs.regenerate_agents_md(root, "<!-- BEGIN -->\nnew managed\n\n")
        self.assertEqual((root / "AGENTS.md").read_text(),
                         "<!-- BEGIN -->\nnew managed\n## Repo-specific additions\n\nmine\n")
        (root / "AGENTS.md").write_text("## Repo-specific additions\nx\n"
                                        "## Repo-specific additions\n")
        with self.assertRaises(rs.RetireError):
            rs.regenerate_agents_md(root, "m\n")

    def test_the_entry_goes_before_the_first_dated_entry(self):
        text = ("# log\n\n## Entry format\n\n```\n## YYYY-MM-DD — x\n```\n\n"
                "## 2026-10-01 — a — edit\n- Eval: none\n")
        out = rs.guidance_insert_entry(text, "## 2026-10-20 — b — remove\n- Eval: n=1\n")
        self.assertLess(out.index("2026-10-20"), out.index("2026-10-01"))
        self.assertGreater(out.index("2026-10-20"), out.index("Entry format"))


def guidance_repo(test) -> Path:
    """A minimal _agent-guidance clone: the fixture checkout, an impact log,
    AGENTS.md, the payload copy, and stand-ins for its two scripts."""
    root = make_guidance_checkout(tmpdir(test, "ag-") / "ag")
    (root / "docs").mkdir()
    (root / "docs" / "guidance-impact.md").write_text(
        "# log\n\n## Entry format\n\nx\n\n## 2026-10-01 — alpha — edit\n- Eval: none\n")
    (root / "AGENTS.md").write_text("<!-- BEGIN -->\nstale\n## Repo-specific additions\n\nmine\n")
    (root / ".claude" / "hooks").mkdir(parents=True, exist_ok=True)
    shutil.copy(root / "agents-md" / "base.md", root / ".claude" / "hooks" / "fleet-guidance.md")
    (root / "scripts").mkdir()
    (root / "scripts" / "check-guidance-coverage.js").write_text("process.exit(0);\n")
    (root / "scripts" / "build-agents-md.sh").write_text("echo '<!-- BEGIN -->'; echo managed\n")
    sh(root, "git", "init", "-q", "-b", "main")
    sh(root, "git", "add", "-A")
    sh(root, "git", "commit", "-q", "-m", "base")
    return root


AUTO_ENV = {"GITHUB_EVENT_NAME": "schedule", "GITHUB_ACTIONS": "true",
            "GITHUB_REF": "refs/heads/main"}


@unittest.skipUnless(shutil.which("node"), "node is needed for the coverage script")
class GuidanceRemovalTests(unittest.TestCase):

    def run_main(self, gates_doc, checkout, env=AUTO_ENV, allow=("auto",), dry=False,
                 fallback=False):
        path = tmpdir(self, "gates-") / "gates.json"
        path.write_text(json.dumps(gates_doc))
        gh, pushed, out = FakeGh(), [], io.StringIO()
        self.registry = FakeGh()
        argv = ["--gates", str(path), "--target", "guidance", "--guidance", str(checkout),
                *[x for a in allow for x in ("--allow-mode", a)], *(["--dry-run"] if dry else []),
                *(["--fallback-to-proposal"] if fallback else [])]
        old = os.environ.copy()
        os.environ.update(GIT_ENV)
        try:
            rc = rs.main(argv, env=env, gh=gh, push=lambda c, b, *_: pushed.append(b),
                         registry_gh=self.registry, out=out)
        finally:
            os.environ.clear()
            os.environ.update(old)
        return rc, gh, pushed, out.getvalue()

    def test_auto_mode_opens_one_auto_merging_removal(self):
        root = guidance_repo(self)
        rc, gh, pushed, out = self.run_main(guidance_gates(mode="auto"), root)
        self.assertEqual(rc, 0, out)
        self.assertEqual(pushed, ["retire-guidance/bravo"])
        # Every write to _agent-guidance goes through registry_gh: the
        # workflow's own token cannot write another repository.
        self.assertEqual([c[0][:2] for c in self.registry.calls],
                         [["pr", "create"], ["api", "-X"], ["pr", "merge"], ["pr", "view"]])
        create, label, merge, _view = self.registry.calls
        self.assertEqual(label[0][-1], f"labels[]={rs.AGENT_LABEL}")
        self.assertIn(f"repos/{rs.GUIDANCE_REPO}/issues/9/labels", label[0][3])
        head = sh(root, "git", "rev-parse", "HEAD").stdout.strip()
        self.assertEqual(merge[0][-4:], ["--auto", "--merge", "--match-head-commit", head])
        self.assertTrue(create[1].rstrip().endswith(rs.AGENT_MARKER))
        self.assertIn(rs.AGENT_TRAILER, sh(root, "git", "log", "-1", "--format=%B").stdout)
        self.assertEqual([c[0][:2] for c in gh.calls if c[0][0] == "pr"], [])
        self.assertEqual(sh(root, "git", "status", "--porcelain").stdout, "")
        changed = sh(root, "git", "show", "--name-only", "--format=", "HEAD").stdout.split()
        self.assertEqual(sorted(changed), sorted([
            ".claude/hooks/fleet-guidance.md", "AGENTS.md", "agents-md/base.md",
            "agents-md/eval-coverage.yml", "docs/guidance-impact.md"]))
        base = (root / "agents-md" / "base.md").read_text()
        self.assertNotIn("## Bravo", base)
        self.assertEqual((root / ".claude/hooks/fleet-guidance.md").read_text(), base)
        ids = [r["id"] for r in yaml.safe_load((root / "agents-md/eval-coverage.yml").read_text())]
        self.assertNotIn("bravo", ids)
        self.assertIn("## 2026-10-20 — bravo — remove",
                      (root / "docs/guidance-impact.md").read_text())
        self.assertEqual((root / "AGENTS.md").read_text(),
                         "<!-- BEGIN -->\nmanaged\n## Repo-specific additions\n\nmine\n")

    def test_auto_mode_notifies_adam_with_the_removal_and_its_reversal(self):
        # #557 (Adam, 2026-11-02): every removal notifies him and says how to
        # reverse it, through this repository's own token.
        root = guidance_repo(self)
        rc, gh, _pushed, out = self.run_main(guidance_gates(mode="auto"), root)
        self.assertEqual(rc, 0, out)
        self.assertIn("removal notice", out)
        notices = [c for c in gh.calls if c[0][:2] == ["issue", "create"]]
        self.assertEqual(len(notices), 1)
        args, body = notices[0]
        self.assertEqual(args[:4], ["issue", "create", "-R", rs.EVALS_REPO])
        self.assertIn(rs.AGENT_LABEL, args)
        pr_url = f"https://github.com/{rs.GUIDANCE_REPO}/pull/9"
        self.assertTrue(body.startswith(rs.GUIDANCE_NOTICE_MARKER.format(section="bravo")))
        self.assertIn(f"@{rs.GUIDANCE_NOTICE_OWNER}", body)
        self.assertIn(pr_url, body)
        self.assertNotIn("{removal_pr}", body)
        self.assertIn("**Revert**", body)
        self.assertTrue(body.rstrip().endswith(rs.AGENT_MARKER))
        # The dry run names the notice too.
        dry = rs.guidance_commands(rs.guidance_plan(guidance_gates(mode="auto"),
                                                    guidance_repo(self), FakeGh(),
                                                    allowed=("auto",)))
        self.assertEqual(dry[-1][:3], ["gh", "issue", "create"])

    def test_proposal_mode_files_an_issue_here_and_touches_no_checkout(self):
        for verdict in ("retire", "shorten-or-merge"):
            root = guidance_repo(self)
            rc, gh, pushed, out = self.run_main(guidance_gates(verdict), root,
                                                allow=("proposal",))
            with self.subTest(verdict=verdict):
                self.assertEqual(rc, 0, out)
                self.assertEqual(pushed, [])
                self.assertEqual(gh.calls[-1][0][:4],
                                 ["issue", "create", "-R", rs.EVALS_REPO])
                self.assertEqual(sh(root, "git", "status", "--porcelain").stdout, "")
                self.assertEqual(sh(root, "git", "branch", "--list").stdout.split(),
                                 ["*", "main"])

    def test_a_removal_without_auto_enabled_on_the_pull_request_is_an_error(self):
        root = guidance_repo(self)
        registry = FakeGh(merge_method="")
        path = tmpdir(self, "gates-") / "gates.json"
        path.write_text(json.dumps(guidance_gates(mode="auto")))
        old = os.environ.copy()
        os.environ.update(GIT_ENV)
        try:
            rc = rs.main(["--gates", str(path), "--target", "guidance", "--guidance",
                          str(root), "--allow-mode", "auto"], env=AUTO_ENV, gh=FakeGh(),
                         push=lambda c, b, *_: None, registry_gh=registry, out=io.StringIO())
        finally:
            os.environ.clear()
            os.environ.update(old)
        self.assertEqual(rc, 2)

    def test_fallback_to_proposal_files_the_issue_when_auto_is_not_allowed(self):
        root = guidance_repo(self)
        rc, gh, pushed, out = self.run_main(guidance_gates(mode="auto"), root,
                                            allow=("proposal",), fallback=True)
        self.assertEqual(rc, 0, out)
        self.assertEqual(pushed, [])
        self.assertEqual(self.registry.calls, [])
        self.assertEqual(gh.calls[-1][0][:4], ["issue", "create", "-R", rs.EVALS_REPO])
        self.assertIn(rs.GUIDANCE_NO_CREDENTIAL, gh.calls[-1][1])
        self.assertEqual(sh(root, "git", "branch", "--list").stdout.split(), ["*", "main"])
        rc, _gh, _pushed, out = self.run_main(guidance_gates(mode="auto"), root,
                                              allow=("proposal",), fallback=True, dry=True)
        self.assertEqual(json.loads(out)["mode_reason"], rs.GUIDANCE_NO_CREDENTIAL)

    def test_a_proposal_only_guidance_verdict_files_the_issue_in_auto_mode(self):
        # The review's surviving mutation (round 1): guidance's `removal !=
        # "auto"` lowering was untested. A verdict that says proposal, or
        # says auto over cells that do not allow it (round 1's m3), files
        # the issue and pushes nothing, with auto allowed.
        for doc in (guidance_gates(mode="auto", removal="proposal"),
                    guidance_gates(mode="auto", classes={"model-b": "no-clear-effect"}),
                    guidance_gates(mode="auto", classes={"model-b": "ceiling"})):
            with self.subTest(removal=doc["guidance"]["bravo"].get("removal"),
                              classes=[c["class"] for c in doc["guidance"]["bravo"]["cells"]]):
                root = guidance_repo(self)
                rc, gh, pushed, out = self.run_main(doc, root, allow=("auto", "proposal"))
                self.assertEqual(rc, 0, out)
                self.assertEqual(pushed, [])
                self.assertEqual(gh.calls[-1][0][:4], ["issue", "create", "-R", rs.EVALS_REPO])
                self.assertEqual(sh(root, "git", "branch", "--list").stdout.split(),
                                 ["*", "main"])
        # Both cells no-benefit and `removal: auto`: the auto path stands.
        self.assertIsNone(rs.proposal_only(guidance_gates(mode="auto")["guidance"]["bravo"]))

    def test_without_fallback_auto_not_allowed_still_exits_2(self):
        root = guidance_repo(self)
        rc, gh, pushed, _out = self.run_main(guidance_gates(mode="auto"), root,
                                             allow=("proposal",))
        self.assertEqual(rc, 2)
        self.assertEqual(pushed, [])
        self.assertEqual(gh.calls, [])

    def test_a_sections_file_section_removes_the_file(self):
        root = guidance_repo(self)
        rc, _gh, _pushed, out = self.run_main(
            guidance_gates(mode="auto", section="section-delta"), root)
        self.assertEqual(rc, 0, out)
        self.assertFalse((root / "agents-md/sections/delta.md").exists())

    def test_auto_mode_outside_actions_or_a_dispatch_is_refused_and_writes_nothing(self):
        root = guidance_repo(self)
        head = sh(root, "git", "rev-parse", "HEAD").stdout
        for env in ({**AUTO_ENV, "GITHUB_ACTIONS": ""},
                    {**AUTO_ENV, "GITHUB_EVENT_NAME": "workflow_dispatch"}):
            rc, gh, pushed, _ = self.run_main(guidance_gates(mode="auto"), root, env=env)
            with self.subTest(env=env):
                self.assertEqual(rc, 2)
                self.assertEqual(pushed, [])
        self.assertEqual(sh(root, "git", "rev-parse", "HEAD").stdout, head)

    def test_a_dry_run_plans_and_writes_nothing(self):
        root = guidance_repo(self)
        rc, gh, pushed, out = self.run_main(guidance_gates(mode="auto"), root, env={}, dry=True)
        self.assertEqual(rc, 0, out)
        plan = json.loads(out)
        self.assertEqual(plan["action"], "guidance-removal")
        self.assertIn(["copy", "agents-md/base.md", ".claude/hooks/fleet-guidance.md"],
                      plan["would_run"])
        self.assertEqual(pushed, [])
        self.assertEqual(sh(root, "git", "status", "--porcelain").stdout, "")


class GuidanceWorkflowTests(unittest.TestCase):
    """skill-coverage.yml's retirement job, read with a YAML parser."""

    def test_the_guidance_step_follows_the_skill_step_with_its_own_scoped_token(self):
        doc = yaml.safe_load((ROOT / ".github/workflows/skill-coverage.yml").read_text())
        steps = doc["jobs"]["retirement"]["steps"]
        checkout = next(s for s in steps if s.get("with", {}).get("repository")
                        == "Adam-S-Daniel/_agent-guidance")
        compute = next(s for s in steps if "scripts/compute_gates.py" in s.get("run", ""))
        acts = [s for s in steps if "scripts/retire_skill.py" in s.get("run", "")
                and "--withdraw-stale" not in s["run"]]
        self.assertEqual(len(acts), 2)
        guidance_act = acts[1]
        self.assertIn("--guidance \"$GITHUB_WORKSPACE/agent-guidance\"", compute["run"])
        self.assertIn("--target guidance", guidance_act["run"])
        self.assertNotIn("--target guidance", acts[0]["run"])
        self.assertIn("modes=(--allow-mode proposal)", guidance_act["run"])
        self.assertIn('if [ -n "$REGISTRY_TOKEN" ]; then\n  modes+=(--allow-mode auto)',
                      guidance_act["run"])
        self.assertIn("modes+=(--fallback-to-proposal)", guidance_act["run"])
        self.assertIn('"${modes[@]}"', guidance_act["run"])
        self.assertEqual(guidance_act["env"], {
            "GH_TOKEN": "${{ github.token }}",
            "REGISTRY_TOKEN": "${{ steps.guidance-token.outputs.token }}"})
        withdraw = steps[steps.index(guidance_act) - 1]
        self.assertIn("--withdraw-stale --target guidance", withdraw["run"])
        mint = steps[steps.index(withdraw) - 1]
        self.assertEqual(mint["id"], "guidance-token")
        self.assertTrue(mint["uses"].startswith("actions/create-github-app-token@"))
        self.assertIs(mint["continue-on-error"], True)
        self.assertEqual(mint["if"], "${{ !cancelled() && steps.verdicts.outcome == 'success' "
                                     "&& steps.credential.outputs.present == 'true' }}")
        self.assertEqual(mint["with"], {
            "client-id": "${{ secrets.EVAL_IMPROVE_APP_CLIENT_ID }}",
            "private-key": "${{ secrets.EVAL_IMPROVE_APP_PEM }}",
            "owner": "Adam-S-Daniel", "repositories": "_agent-guidance",
            "permission-contents": "write", "permission-pull-requests": "write"})
        # Each token reaches one step: the guidance token is not the skill step's.
        self.assertEqual([s for s in steps if "guidance-token" in json.dumps(s)],
                         [mint, withdraw, guidance_act])
        self.assertNotIn("guidance-token", json.dumps(acts[0]))
        self.assertLess(steps.index(checkout), steps.index(compute))
        self.assertIs(checkout["with"]["persist-credentials"], False)
        self.assertEqual(doc["jobs"]["retirement"]["permissions"],
                         {"contents": "read", "issues": "write"})


def _real_checkout_ready() -> bool:
    return all((REAL_GUIDANCE_DIR / p).exists() for p in (
        "scripts/check-guidance-touch.js", "scripts/check-agents-md.sh",
        "scripts/check-fleet-guidance-mirror.js", "node_modules/yaml")) \
        and shutil.which("node") is not None


@unittest.skipUnless(_real_checkout_ready(), f"no prepared _agent-guidance checkout at "
                     f"{REAL_GUIDANCE_DIR} (scripts and node_modules)")
class RealGuidanceRemovalTests(unittest.TestCase):
    """The removal against a local clone of the real _agent-guidance, judged
    by that repository's own checks. The clone has its remote removed and
    the push is a fake, so nothing leaves the scratch directory."""

    def test_a_removal_passes_the_repositorys_own_checks(self):
        clone = tmpdir(self, "ag-real-") / "ag"
        sh(clone.parent, "git", "clone", "-q", "--no-hardlinks", str(REAL_GUIDANCE_DIR),
           str(clone))
        sh(clone, "git", "remote", "remove", "origin")
        (clone / "node_modules").symlink_to(REAL_GUIDANCE_DIR / "node_modules")
        # A symlink does not match the checkout's `node_modules/` ignore rule.
        with open(clone / ".git" / "info" / "exclude", "a", encoding="utf-8") as f:
            f.write("/node_modules\n")
        base = sh(clone, "git", "rev-parse", "HEAD").stdout.strip()
        manifest = yaml.safe_load((clone / "agents-md/eval-coverage.yml").read_text())
        section = next(r["id"] for r in manifest if r["file"] == "agents-md/base.md")
        doc = guidance_gates(mode="auto", section=section)
        doc["as_of"] = sh(clone, "git", "log", "-1", "--format=%cd",
                          "--date=format-local:%Y%m%dT%H%M%SZ",
                          env={"TZ": "UTC"}).stdout.strip()
        rc, _gh, pushed, out = GuidanceRemovalTests.run_main(self, doc, clone)
        self.assertEqual(rc, 0, out)
        head = sh(clone, "git", "rev-parse", "HEAD").stdout.strip()
        event = clone.parent / "event.json"
        event.write_text(json.dumps({"pull_request": {"base": {"sha": base},
                                                      "head": {"sha": head}}}))
        sh(clone, "bash", "scripts/check-agents-md.sh", "AGENTS.md")
        sh(clone, "node", "scripts/check-guidance-coverage.js", "--check-bytes")
        sh(clone, "node", "scripts/check-guidance-touch.js",
           env={"GITHUB_EVENT_PATH": str(event)})
        sh(clone, "node", "scripts/check-fleet-guidance-mirror.js")
        expected = sh(clone, "bash", "-c",
                      "printf '%s\\n%s\\n' \"$(./scripts/build-agents-md.sh)\" "
                      "\"$(sed -n '/^## Repo-specific additions/,$p' AGENTS.md)\"").stdout
        self.assertEqual((clone / "AGENTS.md").read_text(), expected)


if __name__ == "__main__":
    unittest.main()
