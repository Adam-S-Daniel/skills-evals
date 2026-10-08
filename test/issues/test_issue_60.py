"""Offline checks for daily coverage publication and public GAP proposals."""

from __future__ import annotations

import base64
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

import yaml

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
import scaffold_skill_gaps as gaps  # noqa: E402


def world(public_gaps=5):
    registries = []
    totals = {"total": 0, "covered": 0, "skipped": 0, "gap": 0}
    for name, policy in gaps.REGISTRY_POLICY.items():
        private = name in gaps.eval_coverage.PRIVATE_REGISTRIES
        rows = [] if private else [
            {"registry": name, "bundle": None, "skill": f"public-{index}",
             "status": "gap", "fixtures": 0, "reason": None}
            for index in range(public_gaps if name == "adam-agentskills" else 1)]
        counts = {"total": len(rows) if not private else 1,
                  "covered": 0, "skipped": 0,
                  "gap": len(rows) if not private else 1}
        for key in totals:
            totals[key] += counts[key]
        reg = {"name": name, "layout": policy["layout"], "private": private,
               "counts": counts, "skills": rows, "names_withheld": private}
        if not private:
            reg["url"] = policy["url"]
        registries.append(reg)
    census = {"schema": 1, "include_private_names": False,
              "registries": registries, "totals": totals, "problems": []}
    sources = {"repository_revision": "a" * 40,
               "guidance_revision": "b" * 40,
               "registries": {name: "c" * 40 for name in gaps.REGISTRY_POLICY
                              if name not in gaps.eval_coverage.PRIVATE_REGISTRIES}}
    return census, sources


class FakeGitHub:
    def __init__(self, *, hold_parent=False, prs=None, issues=None, children=None):
        self.hold_parent = hold_parent
        self.prs = list(prs or [])
        self.issues = list(issues or [])
        self.children = list(children or [])
        self.calls = []
        self.number = 300

    def pages(self, path):
        self.calls.append(("PAGES", path, None))
        if "/pulls?" in path:
            rows = self.prs
        elif "/sub_issues" in path:
            rows = self.children
        else:
            rows = self.issues
        if "state=open" in path:
            return [item for item in rows if item.get("state", "open") == "open"]
        if "state=closed" in path:
            return [item for item in rows if item.get("state") == "closed"]
        return rows

    def request(self, method, path, payload=None, *, missing_ok=False):
        self.calls.append((method, path, payload))
        if method == "GET":
            if path.endswith("/issues/62"):
                return {"state": "open", "labels":
                        [{"name": "on-hold"}] if self.hold_parent else []}
            if "/contents/" in path or "/git/ref/" in path:
                return None
            if "/git/commits/" in path:
                return {"tree": {"sha": "d" * 40}}
        if path.endswith("/git/blobs"):
            return {"sha": "e" * 40}
        if path.endswith("/git/trees"):
            return {"sha": "f" * 40}
        if path.endswith("/git/commits"):
            return {"sha": "1" * 40}
        if path.endswith("/pulls"):
            self.number += 1
            return {"number": self.number, "body": payload["body"],
                    "html_url": f"https://github.com/{gaps.REPO}/pull/{self.number}",
                    "labels": []}
        if path.endswith("/issues"):
            self.number += 1
            return {"id": self.number, "body": payload["body"], "labels": []}
        return {}


class DraftTests(unittest.TestCase):
    def test_generated_fixture_is_a_context_valid_todo_not_a_claimed_eval(self):
        census, sources = world()
        reg, row = gaps.public_gaps(census)[0]
        files = gaps.draft_files(reg, row, sources)
        fixture = next(content for path, content in files.items()
                       if path.endswith("fixture.yaml"))
        parsed = gaps.context.load_fixture_yaml(fixture, "fixture.yaml")
        self.assertTrue(parsed["draft"])
        self.assertEqual(parsed["context"]["repository"], gaps.REPO)
        self.assertEqual(parsed["context"]["budget"],
                         {"guidance_bytes": 1, "skill_catalog_bytes": 1,
                          "skill_payload_bytes": 1})
        self.assertNotIn("objective_checks", parsed)
        self.assertIn("TODO", parsed["prompt"])
        self.assertTrue(fixture.startswith("# <!-- skill-gap:"))
        self.assertEqual(len(files), 2)

    def test_redacted_artifact_requires_complete_consistent_denominator(self):
        census, _ = world()
        self.assertEqual(len(gaps.public_gaps(census)), 7)
        private = next(reg for reg in census["registries"] if reg["private"])
        private["skills"] = [{"skill": "private-marker"}]
        with self.assertRaises(gaps.GapError):
            gaps.public_gaps(census)
        census, _ = world()
        census["registries"].pop()
        with self.assertRaises(gaps.GapError):
            gaps.public_gaps(census)
        census, _ = world()
        census["registries"][0] = copy.deepcopy(census["registries"][1])
        with self.assertRaises(gaps.GapError):
            gaps.public_gaps(census)

    def test_harness_legal_leading_punctuation_can_be_scaffolded(self):
        census, sources = world(public_gaps=3)
        rows = census["registries"][0]["skills"]
        for row, skill in zip(rows, ("_hidden", "-dash", ".dot")):
            row["skill"] = skill
        actual = gaps.public_gaps(census)
        self.assertEqual([row["skill"] for _, row in actual[:3]],
                         ["_hidden", "-dash", ".dot"])
        self.assertTrue(gaps.branch_name("adam-agentskills", ".dot").endswith(
            "x" + ".dot".encode().hex()))
        self.assertNotEqual(gaps.branch_name("adam-agentskills", "a..b"),
                            gaps.branch_name("adam-agentskills", "x612e2e62"))
        self.assertTrue(gaps.branch_name("adam-agentskills", "ends.lock").endswith(
            "x" + "ends.lock".encode().hex()))
        self.assertTrue(gaps.draft_files(*actual[0], sources))

    def test_census_artifact_has_public_urls_and_no_private_skill_rows(self):
        census, _ = world()
        # The capture wrapper enriches the existing census with source URLs.
        with tempfile.TemporaryDirectory() as tmp:
            resolved = {name: {**policy, "path": Path(tmp)}
                        for name, policy in gaps.REGISTRY_POLICY.items()}
            raw = copy.deepcopy(census)
            for reg in raw["registries"]:
                reg.pop("url", None)
            with (mock.patch.object(gaps.eval_coverage, "run",
                                    return_value=(0, json.dumps(raw))),
                  mock.patch.object(gaps.eval_coverage, "resolve", return_value=resolved),
                  mock.patch.object(gaps, "_revision", return_value="a" * 40)):
                gaps.census([], Path(tmp), Path(tmp) / "out")
            out = json.loads((Path(tmp) / "out" / "coverage.json").read_text())
            self.assertEqual(len(gaps.public_gaps(out)), 7)
            self.assertNotIn("private-marker", json.dumps(out))


class AutomationTests(unittest.TestCase):
    def test_dry_run_makes_no_github_calls_and_selects_at_most_three(self):
        census, sources = world()
        tags = gaps.automate(None, census, sources, "42", "a" * 40, write=False)
        self.assertEqual(len(tags), 3)

    def test_writes_only_coverage_paths_and_three_drafts_with_tracking(self):
        census, sources = world()
        api = FakeGitHub()
        tags = gaps.automate(api, census, sources, "42", "a" * 40, write=True,
                             as_of="2026-10-08T00:00:00Z")
        self.assertEqual(len(tags), 3)
        paths = [path for method, path, _ in api.calls if method == "PUT"]
        self.assertEqual(paths, [f"/repos/{gaps.REPO}/contents/coverage/42.json",
                                 f"/repos/{gaps.REPO}/contents/coverage/latest.json",
                                 f"/repos/{gaps.REPO}/contents/badges/coverage.json"])
        self.assertEqual(sum(path.endswith("/pulls") for method, path, _ in api.calls
                             if method == "POST"), 3)
        self.assertEqual(sum(path.endswith("/issues") for method, path, _ in api.calls
                             if method == "POST"), 3)
        self.assertEqual(sum(path.endswith("/sub_issues") for method, path, _ in api.calls
                             if method == "POST"), 3)
        self.assertEqual(sum(path.endswith("/labels") for method, path, _ in api.calls
                             if method == "POST"), 3)
        self.assertNotIn("private-marker", json.dumps(api.calls))
        latest = next(payload for method, path, payload in api.calls
                      if method == "PUT" and path.endswith("coverage/latest.json"))
        published = json.loads(base64.b64decode(latest["content"]))
        self.assertEqual(published["publication"]["as_of"], "2026-10-08T00:00:00Z")
        badge = next(payload for method, path, payload in api.calls
                     if method == "PUT" and path.endswith("badges/coverage.json"))
        self.assertIn("skipped", base64.b64decode(badge["content"]).decode())

    def test_held_parent_still_gets_census_but_no_proposals(self):
        census, sources = world()
        api = FakeGitHub(hold_parent=True)
        self.assertEqual(gaps.automate(api, census, sources, "42", "a" * 40,
                                       write=True, as_of="2026-10-08T00:00:00Z"), [])
        self.assertFalse(any(method == "POST" for method, _, _ in api.calls))
        self.assertEqual(sum(method == "PUT" for method, _, _ in api.calls), 3)

    def test_exact_marker_and_held_pr_prevent_duplicate_or_paused_work(self):
        census, sources = world()
        tag = gaps.marker("adam-agentskills", "public-0")
        held_pr = {"body": tag, "labels": [{"name": "on-hold"}]}
        other_pr = {"body": gaps.marker("adam-agentskills", "public-10"),
                    "labels": []}
        api = FakeGitHub(prs=[held_pr, other_pr])
        tags = gaps.automate(api, census, sources, "42", "a" * 40, write=True,
                             as_of="2026-10-08T00:00:00Z")
        self.assertNotIn(tag, tags)
        self.assertIn(gaps.marker("adam-agentskills", "public-1"), tags)

    def test_completed_marker_pair_and_subissue_need_no_reproposal(self):
        census, sources = world(public_gaps=1)
        tag = gaps.marker("adam-agentskills", "public-0")
        api = FakeGitHub(prs=[{"body": tag, "labels": []}],
                         issues=[{"body": tag, "labels": [], "id": 123}],
                         children=[{"id": 123}])
        selected = gaps.automate(api, census, sources, "42", "a" * 40,
                                 write=True, as_of="2026-10-08T00:00:00Z")
        self.assertNotIn(tag, selected)

    def test_pr_only_and_issue_only_resume_without_duplicate_counterpart(self):
        census, sources = world(public_gaps=2)
        pr_tag = gaps.marker("adam-agentskills", "public-0")
        issue_tag = gaps.marker("adam-agentskills", "public-1")
        api = FakeGitHub(
            prs=[{"body": pr_tag, "labels": [], "number": 121,
                  "html_url": f"https://github.com/{gaps.REPO}/pull/121"}],
            issues=[{"body": issue_tag, "labels": [], "id": 122}])
        tags = gaps.automate(api, census, sources, "42", "a" * 40,
                             write=True, as_of="2026-10-08T00:00:00Z")
        self.assertIn(pr_tag, tags)
        self.assertIn(issue_tag, tags)
        posts = [(path, payload) for method, path, payload in api.calls if method == "POST"]
        self.assertEqual(sum(path.endswith("/pulls") for path, _ in posts), 2)
        self.assertEqual(sum(path.endswith("/issues") for path, _ in posts), 2)
        self.assertFalse(any(pr_tag in (payload or {}).get("body", "")
                             for path, payload in posts if path.endswith("/pulls")))
        self.assertFalse(any(issue_tag in (payload or {}).get("body", "")
                             for path, payload in posts if path.endswith("/issues")))

    def test_held_tracking_issue_is_not_modified(self):
        census, sources = world(public_gaps=1)
        tag = gaps.marker("adam-agentskills", "public-0")
        api = FakeGitHub(issues=[{"body": tag, "labels": [{"name": "on-hold"}],
                                  "id": 123}])
        selected = gaps.automate(api, census, sources, "42", "a" * 40,
                                 write=True, as_of="2026-10-08T00:00:00Z")
        self.assertNotIn(tag, selected)

    def test_closed_marked_pr_or_issue_is_left_to_a_reviewer(self):
        census, sources = world(public_gaps=2)
        pr_tag = gaps.marker("adam-agentskills", "public-0")
        issue_tag = gaps.marker("adam-agentskills", "public-1")
        api = FakeGitHub(prs=[{"body": pr_tag, "state": "closed", "labels": []}],
                         issues=[{"body": issue_tag, "state": "closed", "labels": [],
                                  "id": 123}])
        selected = gaps.automate(api, census, sources, "42", "a" * 40,
                                 write=True, as_of="2026-10-08T00:00:00Z")
        self.assertNotIn(pr_tag, selected)
        self.assertNotIn(issue_tag, selected)
        self.assertTrue(any("state=all" in path for method, path, _ in api.calls
                            if method == "PAGES"))

    def test_unsafe_sources_or_census_make_zero_api_calls(self):
        census, sources = world()
        sources["registries"]["adam-agentskills-private"] = "d" * 40
        api = FakeGitHub()
        with self.assertRaises(gaps.GapError):
            gaps.automate(api, census, sources, "42", "a" * 40, write=True)
        self.assertEqual(api.calls, [])
        census, sources = world()
        census["registries"][0]["counts"]["gap"] += 1
        with self.assertRaises(gaps.GapError):
            gaps.automate(api, census, sources, "42", "a" * 40, write=True)
        self.assertEqual(api.calls, [])

    def test_older_rerun_archives_but_does_not_replace_latest_or_badge(self):
        census, sources = world(public_gaps=1)
        old = {"publication": {"run_id": "43"}}

        class NewerLatest(FakeGitHub):
            def request(self, method, path, payload=None, *, missing_ok=False):
                if method == "GET" and path.endswith(
                        "/contents/coverage/latest.json?ref=persistent/eval-results"):
                    self.calls.append((method, path, payload))
                    encoded = base64.b64encode(json.dumps(old).encode()).decode()
                    return {"content": encoded[:20] + "\n" + encoded[20:],
                            "sha": "f" * 40}
                return super().request(method, path, payload, missing_ok=missing_ok)

        api = NewerLatest()
        self.assertEqual(gaps.automate(api, census, sources, "42", "a" * 40,
                                      write=True, as_of="2026-10-08T00:00:00Z"), [])
        writes = [path for method, path, _ in api.calls if method == "PUT"]
        self.assertEqual(writes, [f"/repos/{gaps.REPO}/contents/coverage/42.json"])
        self.assertFalse(any(method == "POST" for method, _, _ in api.calls))

    def test_existing_branch_requires_matching_draft_marker(self):
        census, sources = world()
        reg, row = gaps.public_gaps(census)[0]
        files = gaps.draft_files(reg, row, sources)
        branch = gaps.branch_name(reg["name"], row["skill"])

        class ExistingBranch(FakeGitHub):
            def request(self, method, path, payload=None, *, missing_ok=False):
                if "/git/ref/" in path:
                    self.calls.append((method, path, payload))
                    return {"object": {"sha": "1" * 40}}
                if path.endswith("/git/commits/" + "1" * 40):
                    self.calls.append((method, path, payload))
                    return {"parents": [{"sha": "a" * 40}]}
                if "/compare/" in path:
                    self.calls.append((method, path, payload))
                    return {"total_commits": 1, "files": [
                        {"filename": name, "status": "added"} for name in files]}
                if "/contents/" in path:
                    self.calls.append((method, path, payload))
                    fixture = next(content for name, content in files.items()
                                   if name.endswith("fixture.yaml"))
                    encoded = base64.b64encode(fixture.encode()).decode()
                    return {"content": encoded[:40] + "\n" + encoded[40:]}
                return super().request(method, path, payload, missing_ok=missing_ok)

        api = ExistingBranch()
        gaps._ensure_branch(api, branch, files, "a" * 40)
        self.assertFalse(any(method == "POST" for method, _, _ in api.calls))
        bad = {**files}
        fixture_path = next(path for path in bad if path.endswith("fixture.yaml"))
        bad[fixture_path] = bad[fixture_path].replace("skill-gap:", "wrong-gap:")
        with self.assertRaises(gaps.GapError):
            gaps._ensure_branch(api, branch, bad, "a" * 40)

        class ExtraChange(ExistingBranch):
            def request(self, method, path, payload=None, *, missing_ok=False):
                if "/compare/" in path:
                    return {"total_commits": 1, "files": [
                        {"filename": name, "status": "added"} for name in files] +
                        [{"filename": ".github/workflows/unrelated.yml", "status": "added"}]}
                return super().request(method, path, payload, missing_ok=missing_ok)

        with self.assertRaises(gaps.GapError):
            gaps._ensure_branch(ExtraChange(), branch, files, "a" * 40)


class WorkflowTests(unittest.TestCase):
    def setUp(self):
        self.workflow = yaml.load(
            (ROOT / ".github/workflows/skill-coverage.yml").read_text(),
            Loader=yaml.BaseLoader)

    def test_schedule_dispatch_and_main_guard_with_dry_dispatch(self):
        triggers = self.workflow["on"]
        self.assertEqual(set(triggers), {"schedule", "workflow_dispatch"})
        self.assertEqual(triggers["workflow_dispatch"]["inputs"]["dry_run"]["default"],
                         "true")
        self.assertIn("refs/heads/main", self.workflow["jobs"]["census"]["if"])
        condition = self.workflow["jobs"]["publish"]["if"]
        for token in ("refs/heads/main", "schedule", "workflow_dispatch",
                      "inputs.dry_run == false"):
            self.assertIn(token, condition)
        summary = next(step for step in self.workflow["jobs"]["census"]["steps"]
                       if step["name"] == "Summarize the redacted census")
        self.assertIn("$GITHUB_STEP_SUMMARY", summary["run"])
        self.assertEqual(self.workflow["concurrency"],
                         {"group": "skill-coverage-main", "cancel-in-progress": "false"})

    def test_reader_and_writer_permissions_checkout_and_pins(self):
        self.assertEqual(self.workflow["permissions"], {})
        self.assertEqual(self.workflow["jobs"]["census"]["permissions"],
                         {"contents": "read"})
        writer = self.workflow["jobs"]["publish"]
        self.assertEqual(writer["permissions"],
                         {"contents": "write", "pull-requests": "write",
                          "issues": "write"})
        census_steps = self.workflow["jobs"]["census"]["steps"]
        checkouts = [step for step in census_steps if step.get("uses", "").startswith(
            "actions/checkout@")]
        self.assertEqual(len(checkouts), 6)
        self.assertTrue(all(step["with"]["persist-credentials"] == "false"
                            for step in checkouts))
        self.assertIn("SKILL_COVERAGE_READ_TOKEN", json.dumps(census_steps))
        for job in self.workflow["jobs"].values():
            for step in job["steps"]:
                if "uses" in step:
                    action = step["uses"]
                    self.assertEqual(len(action.rsplit("@", 1)[-1]), 40)
                    self.assertTrue(all(c in "0123456789abcdef" for c in
                                        action.rsplit("@", 1)[-1]))
                if "run" in step:
                    self.assertNotIn("${{ github.event.", step["run"])
                    self.assertNotIn("${{ inputs.", step["run"])

    def test_ci_required_check_runs_on_new_workflow_changes(self):
        ci = yaml.load((ROOT / ".github/workflows/ci.yml").read_text(),
                       Loader=yaml.BaseLoader)
        path = ".github/workflows/skill-coverage.yml"
        self.assertIn(path, ci["on"]["push"]["paths"])
        salient = next(step for step in ci["jobs"]["test"]["steps"]
                       if step.get("id") == "salient")
        self.assertIn(path, salient["env"]["SALIENT_PATHS"].splitlines())


if __name__ == "__main__":
    unittest.main()
