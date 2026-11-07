"""Fleet worker fixture pull requests merge themselves only when they just
add fixtures for their fixture-need issue (skills-evals#659 follow-up;
repo-settings ADR 0018)."""

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

import draft_new_skill  # noqa: E402
import fixture_pr_gate as gate  # noqa: E402

REG = "https://github.com/Adam-S-Daniel/adam-agentskills"
REQUEST = "https://github.com/Adam-S-Daniel/skills-evals/issues/42"
#: Every fixture a fix PR adds says where it came from (Adam, 2026-11-03).
ORIGIN = f"origin:\n  kind: invented\n  source: null\n  request: {REQUEST}\n"
SKILL_FIXTURE = f"skill: writing-adrs\nregistry: {REG}\nprompt: Write an ADR.\n{ORIGIN}"
GUIDE_FIXTURE = f"subject: guidance\nsection: example-section\nprompt: Do it.\n{ORIGIN}"
UNSCHEDULED = ("fixtures:\n  - path: evals/other\n    reason: \"kept out\"\n")
SCHEDULED = ("fixtures:\n  - path: evals/writing-adrs/old\n    readiness: \"ok\"\n")


def git(repo, *args):
    subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True)


def issue(number=42, kind="needs-harder-fixtures", key="writing-adrs", **over):
    return {"number": number, "state": "open", "user": {"login": "github-actions[bot]"},
            "body": f"<!-- skills-evals:{kind}:{key} -->\n\ntext\n", **over}


def pr(body="Refs Adam-S-Daniel/skills-evals#42", **over):
    repo = {"full_name": "Adam-S-Daniel/skills-evals"}
    return {"user": {"login": "Adam-S-Daniel"}, "labels": [{"name": "agent-authored"}],
            "head": {"repo": repo}, "base": {"repo": repo}, "body": body, **over}


class FixturePrGateTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.repo = Path(self.tmp.name)
        git(self.repo, "init", "-q", "-b", "main")
        git(self.repo, "config", "user.email", "t@example.com")
        git(self.repo, "config", "user.name", "t")
        self.write("evals/writing-adrs/old/fixture.yaml", SKILL_FIXTURE)
        self.write("evals/unscheduled.yml", UNSCHEDULED)
        self.write("evals/scheduled.yml", SCHEDULED)
        self.write("README.md", "x\n")
        self.commit("base")
        git(self.repo, "checkout", "-q", "-b", "pr")

    def tearDown(self):
        self.tmp.cleanup()

    def write(self, rel, text):
        path = self.repo / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    def commit(self, message):
        git(self.repo, "add", "-A")
        git(self.repo, "commit", "-q", "-m", message)

    def judge(self, the_pr=None, issues=None):
        self.commit("change")
        return gate.classify(self.repo, "main", "pr", the_pr or pr(),
                             [issue()] if issues is None else issues)

    def add_skill_fixture(self, name="harder"):
        self.write(f"evals/writing-adrs/{name}/fixture.yaml", SKILL_FIXTURE)
        self.write(f"evals/writing-adrs/{name}/seed/README.md", "seed\n")
        doc = yaml.safe_load(UNSCHEDULED)
        doc["fixtures"].append({"path": f"evals/writing-adrs/{name}",
                                "reason": draft_new_skill.ISOLATION_REASON})
        self.write("evals/unscheduled.yml", yaml.safe_dump(doc, sort_keys=False))

    def test_a_new_skill_fixture_listed_for_contextualizing_is_eligible(self):
        self.add_skill_fixture()
        result = self.judge()
        self.assertEqual((result["lane"], result["eligible"], result["issue"]), (True, True, 42))

    def test_a_new_guidance_fixture_on_the_schedule_is_eligible(self):
        self.write("evals/guidance/example-section/new/fixture.yaml", GUIDE_FIXTURE)
        doc = yaml.safe_load(SCHEDULED)
        doc["fixtures"].append({"path": "evals/guidance/example-section/new",
                                "readiness": "hermetic"})
        self.write("evals/scheduled.yml", yaml.safe_dump(doc, sort_keys=False))
        result = self.judge(issues=[issue(kind="needs-fixtures",
                                          key="guidance/example-section")])
        self.assertTrue(result["eligible"], result["reason"])

    def test_out_of_lane_pull_requests_are_left_alone(self):
        self.add_skill_fixture()
        for the_pr, issues in (
                (pr(user={"login": "someone"}), None),
                (pr(labels=[]), None),
                (pr(head={"repo": {"full_name": "fork/skills-evals"}}), None),
                (pr(body="no reference"), None),
                (pr(), [issue(user={"login": "Adam-S-Daniel"})]),
                (pr(), [issue(state="closed")]),
                (pr(), [issue(body="no marker")]),
                (pr(body="Refs #42 and Refs #43"), [issue(), issue(number=43)])):
            with self.subTest(pr=the_pr, issues=issues):
                result = gate.classify(self.repo, "main", "HEAD", the_pr,
                                       [issue()] if issues is None else issues)
                self.assertEqual((result["lane"], result["eligible"]), (False, False))

    def test_closes_and_full_urls_count_as_references(self):
        self.add_skill_fixture()
        self.commit("change")
        for body in ("Closes #42", "fixes https://github.com/Adam-S-Daniel/skills-evals/issues/42"):
            with self.subTest(body=body):
                self.assertTrue(gate.classify(self.repo, "main", "pr", pr(body=body),
                                              [issue()])["eligible"])

    def test_anything_more_than_new_fixtures_is_not_eligible(self):
        cases = {
            "edits an existing fixture": lambda: (
                self.add_skill_fixture(),
                self.write("evals/writing-adrs/old/fixture.yaml", SKILL_FIXTURE + "x: 1\n")),
            "touches code": lambda: (self.add_skill_fixture(), self.write("scripts/x.py", "")),
            "another subject": lambda: self.write("evals/other-skill/new/fixture.yaml",
                                                  SKILL_FIXTURE),
            "wrong skill in yaml": lambda: self.write(
                "evals/writing-adrs/new/fixture.yaml", "skill: other\nregistry: " + REG + "\n"),
            "a draft": lambda: self.write("evals/writing-adrs/new/fixture.yaml",
                                          SKILL_FIXTURE + "draft: true\n"),
            "no fixture.yaml": lambda: self.write("evals/writing-adrs/new/seed/a.txt", "a\n"),
            "loose file": lambda: self.write("evals/writing-adrs/notes.md", "a\n"),
            "nothing added": lambda: self.write("README.md", "y\n"),
            "wrong list": lambda: (
                self.add_skill_fixture(),
                self.write("evals/scheduled.yml", SCHEDULED
                           + "  - path: evals/writing-adrs/harder\n    readiness: x\n")),
            "rewrites an entry": lambda: (
                self.add_skill_fixture(),
                self.write("evals/unscheduled.yml",
                           (self.repo / "evals/unscheduled.yml").read_text()
                           .replace("kept out", "changed"))),
            "wrong reason": lambda: (
                self.add_skill_fixture(),
                self.write("evals/unscheduled.yml",
                           (self.repo / "evals/unscheduled.yml").read_text()
                           .replace("Isolation pair", "Something"))),
        }
        for name, change in cases.items():
            with self.subTest(case=name):
                git(self.repo, "checkout", "-q", "-B", "pr", "main")
                change()
                result = self.judge()
                self.assertTrue(result["lane"])
                self.assertFalse(result["eligible"], name)

    def test_a_new_fixture_needs_a_valid_origin(self):
        # Adam, 2026-11-03 (skills-evals#656): real fleet work or invented,
        # always recorded, and always naming the request it answers.
        base = f"skill: writing-adrs\nregistry: {REG}\nprompt: Write an ADR.\n"
        real = "https://github.com/Adam-S-Daniel/example-repo/pull/7"
        bad = {
            "missing": ("", "no origin mapping"),
            "not a mapping": ("origin: real-work\n", "no origin mapping"),
            "an extra key": (ORIGIN + "  note: x\n", "no origin mapping"),
            "bad kind": (ORIGIN.replace("invented", "scraped"), "kind is not"),
            "real work without a URL": (ORIGIN.replace("invented", "real-work"),
                                        "not a pull request URL"),
            "real work naming an issue": (
                ORIGIN.replace("invented", "real-work").replace(
                    "null", real.replace("/pull/", "/issues/")), "not a pull request URL"),
            "real work outside the fleet": (
                ORIGIN.replace("invented", "real-work").replace(
                    "null", "https://github.com/someone-else/example-repo/pull/7"),
                "not in a fleet owner's repository"),
            "invented with a source": (ORIGIN.replace("null", real), "source is not null"),
            "another issue": (ORIGIN.replace("/issues/42", "/issues/43"),
                              "not the issue this pull request answers"),
            "another repository's issue": (ORIGIN.replace("skills-evals/issues",
                                                          "other/issues"),
                                           "not the issue this pull request answers"),
        }
        for name, (origin, reason) in bad.items():
            with self.subTest(case=name):
                git(self.repo, "checkout", "-q", "-B", "pr", "main")
                self.add_skill_fixture()
                self.write("evals/writing-adrs/harder/fixture.yaml", base + origin)
                result = self.judge()
                self.assertEqual((result["lane"], result["eligible"]), (True, False), name)
                self.assertIn(reason, result["reason"])
        good = {
            "invented": ORIGIN,
            "real work, first owner": ORIGIN.replace("invented", "real-work")
                                            .replace("null", real),
            "real work, second owner, any case": ORIGIN.replace("invented", "real-work")
                .replace("null", "https://github.com/JodiDaniel/example-site/pull/12"),
        }
        for name, origin in good.items():
            with self.subTest(case=name):
                git(self.repo, "checkout", "-q", "-B", "pr", "main")
                self.add_skill_fixture()
                self.write("evals/writing-adrs/harder/fixture.yaml", base + origin)
                result = self.judge()
                self.assertTrue(result["eligible"], result["reason"])

    def test_a_guidance_fixture_needs_a_valid_origin_too(self):
        self.write("evals/guidance/example-section/new/fixture.yaml",
                   GUIDE_FIXTURE.replace(ORIGIN, ""))
        doc = yaml.safe_load(SCHEDULED)
        doc["fixtures"].append({"path": "evals/guidance/example-section/new",
                                "readiness": "hermetic"})
        self.write("evals/scheduled.yml", yaml.safe_dump(doc, sort_keys=False))
        result = self.judge(issues=[issue(kind="needs-fixtures",
                                          key="guidance/example-section")])
        self.assertFalse(result["eligible"])
        self.assertIn("no origin mapping", result["reason"])

    def test_origin_problem_without_an_issue_accepts_any_request(self):
        origin = {"kind": "invented", "source": None, "request": REQUEST}
        self.assertIsNone(gate.origin_problem(origin))
        self.assertIsNone(gate.origin_problem({**origin, "request": REQUEST[:-2] + "7"}))
        self.assertIsNotNone(gate.origin_problem({**origin, "request": REQUEST + "/x"}))
        self.assertEqual(gate.stakes.FLEET_OWNERS, ("Adam-S-Daniel", "jodidaniel"))

    def test_the_harness_loads_a_fixture_with_an_origin(self):
        # The extra top-level key reaches no whitelist: run_eval loads it,
        # and its mapping-key check passes it through.
        sys.path.insert(0, str(ROOT / "harness"))
        import run_eval
        self.write("evals/writing-adrs/new/fixture.yaml", SKILL_FIXTURE)
        fixture = run_eval.load_fixture(self.repo / "evals/writing-adrs/new")
        self.assertEqual(fixture["origin"]["kind"], "invented")
        run_eval.validate_mapping_keys(fixture, self.repo / "evals/writing-adrs/new")

    def test_a_symlink_is_not_eligible(self):
        self.add_skill_fixture()
        (self.repo / "evals/writing-adrs/harder/link").symlink_to("../old")
        self.assertFalse(self.judge()["eligible"])

    def test_the_cli_prints_outputs_only(self):
        self.add_skill_fixture()
        self.commit("change")
        pr_file, issues_file = self.repo / "pr.json", self.repo / "issues.json"
        pr_file.write_text(json.dumps(pr()), encoding="utf-8")
        issues_file.write_text(json.dumps([issue()]), encoding="utf-8")
        import io
        out = io.StringIO()
        code = gate.main(["classify", "--repo", str(self.repo), "--base", "main",
                          "--source", "pr", "--pr", str(pr_file), "--issues",
                          str(issues_file)], out=out)
        self.assertEqual(code, 0)
        self.assertEqual(out.getvalue().splitlines()[:3],
                         ["lane=true", "eligible=true", "issue=42"])


def trigger_set(positive=10, negative=10, **extra):
    items = [{"query": f"Please record why we chose option {i}", "should_trigger": True}
             for i in range(positive)]
    items += [{"query": f"Summarize meeting notes number {i}", "should_trigger": False}
              for i in range(negative)]
    return json.dumps(items, indent=2) + "\n"


SET_PATH = "evals/writing-adrs/trigger-eval-set.json"


class TriggerSetGateTests(unittest.TestCase):
    """skills-evals#662: a needs-trigger-set issue is answered by one new
    evals/<skill>/trigger-eval-set.json and nothing else."""

    # The same scratch repository as FixturePrGateTests, without its tests.
    setUp, tearDown = FixturePrGateTests.setUp, FixturePrGateTests.tearDown
    write, commit, judge = FixturePrGateTests.write, FixturePrGateTests.commit, \
        FixturePrGateTests.judge
    add_skill_fixture = FixturePrGateTests.add_skill_fixture

    def judge_set(self, issues=None):
        return self.judge(issues=issues or [issue(kind="needs-trigger-set")])

    def test_one_valid_new_trigger_set_is_eligible(self):
        self.write(SET_PATH, trigger_set())
        result = self.judge_set()
        self.assertEqual((result["lane"], result["eligible"], result["issue"]), (True, True, 42))
        self.assertEqual(result["reason"], "adds the trigger set for writing-adrs")
        # The repository's own example set passes the same check.
        self.assertTrue(gate.trigger_set_ok(
            (ROOT / SET_PATH).read_bytes()))

    def test_anything_else_is_not_eligible(self):
        minimum = gate.propose_skill_edit.TRIGGER_ONLY_MIN_CLASS
        cases = {
            "a second file": lambda: (self.write(SET_PATH, trigger_set()),
                                      self.write("evals/writing-adrs/notes.md", "a\n")),
            "bad JSON": lambda: self.write(SET_PATH, "[{"),
            "not the shape": lambda: self.write(SET_PATH, json.dumps(
                [{"query": "x", "should_trigger": "true"}] * 20)),
            "one class": lambda: self.write(SET_PATH, trigger_set(negative=0)),
            "too small": lambda: self.write(SET_PATH, trigger_set(minimum - 1, minimum)),
            # Duplicates count once, as the loop dedupes them.
            "duplicates": lambda: self.write(SET_PATH, json.dumps(
                [{"query": "Record why", "should_trigger": True}] * minimum
                + [{"query": f"Other {i}", "should_trigger": False}
                   for i in range(minimum)])),
            "wrong skill": lambda: self.write("evals/other-skill/trigger-eval-set.json",
                                              trigger_set()),
            "wrong name": lambda: self.write("evals/writing-adrs/triggers.json",
                                             trigger_set()),
            "a fixture instead": lambda: self.add_skill_fixture(),
        }
        for name, change in cases.items():
            with self.subTest(case=name):
                git(self.repo, "checkout", "-q", "-B", "pr", "main")
                change()
                result = self.judge_set()
                self.assertTrue(result["lane"])
                self.assertFalse(result["eligible"], name)

    def test_the_readme_layout_line_for_the_skill_is_allowed(self):
        # skills-evals#744: every trigger-set pull request also lists the
        # skill's directory in README.md's layout; that one line may ride.
        for line in ("  writing-adrs/", "  writing-adrs/  # reviewed trigger-eval-set.json only"):
            with self.subTest(line=line):
                git(self.repo, "checkout", "-q", "-B", "pr", "main")
                self.write(SET_PATH, trigger_set())
                self.write("README.md", f"x\n{line}\n")
                result = self.judge_set()
                self.assertTrue(result["eligible"], result["reason"])

    def test_any_other_readme_change_is_not_eligible(self):
        cases = {
            "two lines": "x\n  writing-adrs/\n  more/\n",
            "a removed line": "  writing-adrs/\n",
            "a changed line": "y\n  writing-adrs/\n",
            "another skill": "x\n  other-skill/\n",
            "not indented": "x\nwriting-adrs/\n",
            "text after the entry": "x\n  writing-adrs/ see https://example.com\n",
            "too long": "x\n  writing-adrs/  # " + "a" * gate.README_LINE_MAX + "\n",
        }
        for name, text in cases.items():
            with self.subTest(case=name):
                git(self.repo, "checkout", "-q", "-B", "pr", "main")
                self.write(SET_PATH, trigger_set())
                self.write("README.md", text)
                self.assertFalse(self.judge_set()["eligible"], name)
        with self.subTest(case="README.md alone"):
            git(self.repo, "checkout", "-q", "-B", "pr", "main")
            self.write("README.md", "x\n  writing-adrs/\n")
            self.assertFalse(self.judge_set()["eligible"])
        with self.subTest(case="README.md made executable"):
            git(self.repo, "checkout", "-q", "-B", "pr", "main")
            self.write(SET_PATH, trigger_set())
            self.write("README.md", "x\n  writing-adrs/\n")
            (self.repo / "README.md").chmod(0o755)
            self.assertFalse(self.judge_set()["eligible"])

    def test_an_executable_set_is_not_eligible(self):
        self.write(SET_PATH, trigger_set())
        (self.repo / SET_PATH).chmod(0o755)
        self.assertFalse(self.judge_set()["eligible"])

    def test_an_existing_set_is_not_eligible(self):
        git(self.repo, "checkout", "-q", "main")
        self.write(SET_PATH, trigger_set())
        self.commit("existing set")
        git(self.repo, "checkout", "-q", "-B", "pr", "main")
        self.write(SET_PATH, trigger_set(12, 12))
        self.assertFalse(self.judge_set()["eligible"])
        # Added on the base after the branch point: also refused.
        git(self.repo, "checkout", "-q", "-B", "pr2", "main~1")
        self.write(SET_PATH, trigger_set())
        self.commit("change")
        self.assertFalse(gate.classify(self.repo, "main", "pr2", pr(),
                                       [issue(kind="needs-trigger-set")])["eligible"])

    def test_a_fixture_need_issue_does_not_admit_a_trigger_set(self):
        self.write(SET_PATH, trigger_set())
        self.assertFalse(self.judge(issues=[issue()])["eligible"])


class FixturePrWorkflowTests(unittest.TestCase):
    def load(self, name):
        return yaml.safe_load((ROOT / ".github/workflows" / name).read_text(encoding="utf-8"))

    def test_the_signal_holds_nothing_and_the_gate_runs_the_default_branch(self):
        seen = self.load("fixture-pr-seen.yml")
        self.assertEqual(seen["permissions"], {})
        steps = seen["jobs"]["signal"]["steps"]
        self.assertTrue(all("uses" not in s for s in steps))
        gate_doc = self.load("fixture-pr-gate.yml")
        trigger = gate_doc[True]
        self.assertEqual(set(trigger), {"workflow_run"})
        self.assertEqual(trigger["workflow_run"]["workflows"], [seen["name"]])
        jobs = gate_doc["jobs"]
        checkout = jobs["judge"]["steps"][0]
        self.assertEqual(checkout["with"]["ref"], "${{ github.event.repository.default_branch }}")
        self.assertIs(checkout["with"]["persist-credentials"], False)
        self.assertEqual(jobs["arm"]["permissions"], {})
        self.assertIn("lane == 'true'", jobs["disarm"]["if"])
        # Disabling auto-merge needs repository write access; with
        # contents: read the job token is refused and the PR merges anyway
        # (skills-evals#744).
        self.assertEqual(
            jobs["disarm"]["permissions"],
            {"contents": "write", "pull-requests": "write"},
        )
        for job in jobs.values():
            self.assertNotIn("concurrency", job)
            for step in job["steps"]:
                self.assertNotIn("${{", step.get("run", ""))
                if "ROSTER_APP_PRIVATE_KEY" in str(step):
                    self.assertIs(step.get("continue-on-error"), True)


    def test_disarm_uses_the_app_token_with_the_job_token_as_fallback(self):
        # 2026-11-04: the job token with `contents: read` was refused
        # ("Resource not accessible by integration
        # (disablePullRequestAutoMerge)") and #744 merged while ineligible.
        disarm = self.load("fixture-pr-gate.yml")["jobs"]["disarm"]
        self.assertEqual(disarm["permissions"], {"contents": "write", "pull-requests": "write"})
        mint, turn_off = disarm["steps"]
        self.assertTrue(mint["uses"].startswith("actions/create-github-app-token@"))
        self.assertEqual(mint["id"], "app-token")
        self.assertIs(mint["continue-on-error"], True)
        self.assertEqual(turn_off["env"]["APP_TOKEN"], "${{ steps.app-token.outputs.token }}")
        self.assertEqual(turn_off["env"]["JOB_TOKEN"], "${{ github.token }}")
        self.assertNotIn("GH_TOKEN", turn_off["env"])
        run = turn_off["run"]
        self.assertIn('*) token="$APP_TOKEN" ;;', run)
        merges = [line.strip() for line in run.splitlines() if "pr merge" in line]
        self.assertEqual(merges, ['if ! GH_TOKEN="$token" GITHUB_TOKEN="" gh pr merge "$NUMBER" '
                                  '--repo "$REPO" --disable-auto > /dev/null; then'])
        # A failed disable, or one that does not read back as off, is red.
        self.assertEqual(run.count("exit 1"), 3)

if __name__ == "__main__":
    unittest.main()
