"""Issue #72: the adamdaniel.ai site sync for the explorer page.

Workflows are parsed with PyYAML, never a line scan. The sync script runs
against a throwaway local site repo with SITE_SYNC_DRY_RUN=1, so nothing is
pushed and no network is touched.
"""

from __future__ import annotations

import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

import yaml

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "test"))
from lockfile_pins import lock_problem  # noqa: E402
WORKFLOWS = ROOT / ".github" / "workflows"
SCRIPT = ROOT / "scripts" / "sync_to_site.sh"
SLUG = "skills-evals"


def load(name: str) -> dict:
    return yaml.safe_load((WORKFLOWS / name).read_text(encoding="utf-8"))


def triggers(doc: dict) -> dict:
    # A bare `on:` key parses as the YAML 1.1 boolean True.
    return doc.get("on", doc.get(True))


def steps(doc: dict):
    for job_id, job in doc["jobs"].items():
        for step in job["steps"]:
            yield job_id, step


class SiteWorkflowTests(unittest.TestCase):
    def setUp(self):
        self.sync = load("site-sync.yml")
        self.preview = load("site-preview.yml")

    def test_sync_triggers(self):
        on = triggers(self.sync)
        self.assertEqual(set(on), {"push", "workflow_dispatch"})
        self.assertEqual(on["push"]["branches"], ["main"])
        self.assertEqual(on["push"]["paths"], ["tool/index.html"])

    def test_preview_triggers(self):
        on = triggers(self.preview)
        self.assertEqual(set(on), {"pull_request"})
        self.assertEqual(on["pull_request"],
                         {"types": ["opened", "synchronize", "reopened", "closed"]})

    def test_no_personal_access_token(self):
        for name in ("site-sync.yml", "site-preview.yml"):
            text = (WORKFLOWS / name).read_text(encoding="utf-8")
            self.assertNotIn("SITE_SYNC_TOKEN", text, name)

    def test_token_mint_is_scoped_and_soft(self):
        for name, doc in (("sync", self.sync), ("preview", self.preview)):
            mints = [s for _, s in steps(doc)
                     if str(s.get("uses", "")).startswith("actions/create-github-app-token@")]
            self.assertTrue(mints, name)
            for step in mints:
                self.assertIs(step.get("continue-on-error"), True, name)
                if name == "sync":
                    # The target follows SITE_REPO, which has no default.
                    self.assertEqual(step["with"]["repositories"],
                                     "${{ steps.site.outputs.name }}")
                    self.assertEqual(step["with"]["owner"], "${{ steps.site.outputs.owner }}")
                else:
                    self.assertEqual(step["with"]["repositories"],
                                     "${{ steps.site.outputs.name }}")
                    self.assertEqual(step["with"]["owner"], "${{ steps.site.outputs.owner }}")
                self.assertIn("EVAL_IMPROVE_APP_CLIENT_ID", step["with"]["client-id"])
                self.assertIn("EVAL_IMPROVE_APP_PEM", step["with"]["private-key"])

    def test_missing_token_fails_the_sync_but_not_the_preview(self):
        decide = [s for _, s in steps(self.sync) if s.get("id") == "token"]
        self.assertEqual(len(decide), 1)
        run = decide[0]["run"]
        self.assertIn("::error::", run)
        self.assertNotIn("::warning::", run)
        self.assertIn("exit 1", run)
        self.assertIn("GITHUB_STEP_SUMMARY", run)
        # Both causes fail: credentials missing, and a mint that failed.
        self.assertIn("could not be minted", run)
        self.assertIn("credentials are not set", run)
        self.assertIn("steps.site.outputs.skip != 'true'", decide[0]["if"])

    def test_missing_token_warns_and_succeeds_in_the_preview(self):
        for name, doc in (("sync", self.sync), ("preview", self.preview)):
            decide = [s for _, s in steps(doc) if s.get("id") == "token"]
            self.assertEqual(len(decide), 1, name)
            run = decide[0]["run"]
            if name == "preview":
                self.assertIn("::warning::", run, name)
                self.assertIn("GITHUB_STEP_SUMMARY", run, name)
                self.assertNotIn("exit 1", run, name)
            self.assertIn("eval-improve GitHub App on the site repository named by SITE_REPO",
                          doc["env"]["FIX_HINT"], name)
            self.assertNotIn("Adam-S-Daniel", doc["env"]["FIX_HINT"], name)

    def test_site_repo_comes_from_a_variable_and_none_skips_cleanly(self):
        self.assertEqual(self.sync["env"]["SITE_REPO"], "${{ vars.SITE_REPO }}")
        self.assertEqual(self.preview["env"]["SITE_REPO"], "${{ vars.SITE_REPO }}")
        resolve = [s for _, s in steps(self.sync) if s.get("id") == "site"]
        self.assertEqual(len(resolve), 1)
        run = resolve[0]["run"]
        self.assertIn('[ "$SITE_REPO" = none ]', run)
        # Unset fails, naming the variable and where to set it.
        self.assertIn('[ -z "$SITE_REPO" ]', run)
        self.assertIn("SITE_REPO is not set", run)
        self.assertIn("Settings > Secrets and variables > Actions > Variables", run)
        self.assertIn("::notice::", run)
        self.assertIn("skip=true", run)
        # Every step that touches the site waits on the skip output.
        gated = {s.get("id") or s.get("name") for _, s in steps(self.sync)
                 if "steps.site.outputs.skip" in str(s.get("if", ""))}
        self.assertTrue({"credential", "mint", "token"} <= gated, gated)
        checkout = [s for _, s in steps(self.sync) if s.get("name") == "Checkout site repo"][0]
        self.assertEqual(checkout["with"]["repository"], "${{ env.SITE_REPO }}")
        preview_checkout = [s for _, s in steps(self.preview)
                            if s.get("name") == "Checkout site repo"][0]
        self.assertEqual(preview_checkout["with"]["repository"], "${{ env.SITE_REPO }}")
        for _, doc in (("sync", self.sync), ("preview", self.preview)):
            for step in [s for _, s in steps(doc) if s.get("id") == "site"]:
                self.assertIn("SITE_REPO is not set", step["run"])

    def test_preview_url_comes_from_a_variable_and_fails_when_missing(self):
        self.assertEqual(self.preview["env"]["SITE_PREVIEW_URL"], "${{ vars.SITE_PREVIEW_URL }}")
        text = (WORKFLOWS / "site-preview.yml").read_text(encoding="utf-8")
        self.assertNotIn("preview-pr${SITE_PR}", text)
        resolve = [s for job_id, s in steps(self.preview)
                   if job_id == "mirror" and s.get("id") == "site"][0]

        def run(**env):
            base = {"PATH": os.environ["PATH"], "GITHUB_OUTPUT": os.devnull}
            base.update(env)
            return subprocess.run(["bash", "-c", resolve["run"]], env=base,
                                  capture_output=True, text=True)

        site = {"SITE_REPO": "example-owner/example-site"}
        unset = run(**site)
        self.assertEqual(unset.returncode, 1)
        self.assertIn("SITE_PREVIEW_URL is not set", unset.stdout)
        self.assertEqual(run(SITE_PREVIEW_URL="https://example.com/x/", **site).returncode, 1)
        self.assertEqual(run(SITE_PREVIEW_URL="http://pr{pr}.example.com/", **site).returncode, 1)
        self.assertEqual(run(SITE_PREVIEW_URL="https://pr{pr}.example.com/t/", **site).returncode, 0)
        self.assertEqual(run(SITE_REPO="none").returncode, 0)
        comment = [s for _, s in steps(self.preview)
                   if s.get("name") == "Comment the preview URLs here"][0]
        line = [l.strip() for l in comment["run"].splitlines() if l.strip().startswith("page_url=")][0]
        out = subprocess.run(["bash", "-c", line + '; printf %s "$page_url"'],
                             env={"PATH": os.environ["PATH"], "SITE_PR": "12",
                                  "SITE_PREVIEW_URL": "https://pr{pr}.example.com/t/"},
                             capture_output=True, text=True)
        self.assertEqual(out.stdout, "https://pr12.example.com/t/")

    def test_permissions_are_minimal(self):
        self.assertEqual(self.sync["permissions"], {"contents": "read"})
        self.assertEqual(self.preview["permissions"],
                         {"contents": "read", "pull-requests": "write"})
        for _, doc in (("sync", self.sync), ("preview", self.preview)):
            for job in doc["jobs"].values():
                self.assertNotIn("permissions", job)

    def test_no_event_expression_inside_run(self):
        for name, doc in (("sync", self.sync), ("preview", self.preview)):
            for job_id, step in steps(doc):
                self.assertNotIn("${{ github.event", step.get("run", ""),
                                 f"{name}/{job_id}/{step.get('name')}")
                self.assertNotIn("${{", step.get("run", ""),
                                 f"{name}/{job_id}/{step.get('name')}: pass values via env:")

    def test_site_coordinates(self):
        self.assertEqual(self.sync["env"]["SYNC_BRANCH"], f"tool-sync/{SLUG}")
        self.assertEqual(self.preview["env"]["PREVIEW_BRANCH"],
                         f"tool-preview/{SLUG}-pr-${{{{ github.event.pull_request.number }}}}")
        text = (WORKFLOWS / "site-preview.yml").read_text(encoding="utf-8")
        # One site page, /tools/evals/, serves both views (Adam, 2026-11-02).
        self.assertIn("/tools/evals/", text)
        self.assertNotIn("/tools/guidance-evals/", text)
        merge = [s["run"] for _, s in steps(self.sync) if "gh pr merge" in s.get("run", "")]
        self.assertEqual(len(merge), 1)
        self.assertIn("--auto --squash", merge[0])

    def test_preview_checks_the_page_path(self):
        rel = [s for _, s in steps(self.preview) if s.get("id") == "relevance"][0]
        self.assertIn("tool/index.html", rel["run"])

    def test_every_uses_is_locked(self):
        for name, doc in (("site-sync.yml", self.sync), ("site-preview.yml", self.preview)):
            for _, step in steps(doc):
                if "uses" in step:
                    with self.subTest(workflow=name, uses=step["uses"]):
                        self.assertIsNone(lock_problem(step["uses"], WORKFLOWS / name))

    def test_source_checkout_does_not_persist_credentials(self):
        # The site checkout must keep its token (the script pushes with it).
        for name, doc in (("sync", self.sync), ("preview", self.preview)):
            for _, step in steps(doc):
                if str(step.get("uses", "")).startswith("actions/checkout@") \
                        and "repository" not in step.get("with", {}):
                    self.assertIs(step["with"].get("persist-credentials"), False, name)

    def test_concurrency_groups_present(self):
        self.assertTrue(self.sync["concurrency"]["cancel-in-progress"])
        self.assertTrue(self.preview["concurrency"]["cancel-in-progress"])


def git(cwd, *args, env=None):
    return subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True,
                          text=True, env=env).stdout.strip()


class SyncScriptTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp, True)
        tmp = Path(self.tmp)
        self.site = tmp / "site"
        (self.site / "assets" / "tools" / SLUG).mkdir(parents=True)
        (self.site / "assets" / "tools" / SLUG / "index.html").write_text("old\n")
        for cmd in (["init", "-q", "-b", "main"], ["add", "-A"]):
            git(self.site, *cmd)
        git(self.site, "-c", "user.name=t", "-c", "user.email=t@example.com",
            "commit", "-q", "-m", "seed")
        self.out = tmp / "github_output"
        self.src_commit = git(ROOT, "rev-parse", "HEAD")
        self.page = ROOT / "tool" / "index.html"

    def run_script(self, site=None, **extra):
        env = {k: v for k, v in os.environ.items() if not k.startswith("GITHUB_")}
        env.update({
            "SITE_DIR": str(site or self.site), "BRANCH": f"tool-preview/{SLUG}-pr-7",
            "SOURCE_COMMIT": self.src_commit, "SOURCE_REF": "pr-7", "SOURCE_PR": "7",
            "COMMIT_MSG": "tools: preview test", "SITE_SYNC_DRY_RUN": "1",
            "GITHUB_OUTPUT": str(self.out),
        })
        env.update(extra)
        return subprocess.run(["bash", str(SCRIPT)], env=env, capture_output=True,
                              text=True, timeout=60, check=False)

    def test_copies_page_verbatim_and_writes_provenance(self):
        if not self.page.exists():
            self.skipTest("tool/index.html is absent")
        proc = self.run_script()
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        asset = self.site / "assets" / "tools" / SLUG / "index.html"
        self.assertEqual(asset.read_bytes(), self.page.read_bytes())
        prov = yaml.safe_load((self.site / "_data" / "tool_sources" / f"{SLUG}.yml")
                              .read_text(encoding="utf-8"))
        self.assertEqual(prov["repo"], "Adam-S-Daniel/skills-evals")
        self.assertEqual(prov["ref"], "pr-7")
        self.assertEqual(prov["commit"], self.src_commit)
        self.assertEqual(prov["source_pr"], 7)
        self.assertIn("source_committed_at", prov)
        self.assertIn("changed=true", self.out.read_text())
        self.assertEqual(git(self.site, "branch", "--show-current"),
                         f"tool-preview/{SLUG}-pr-7")
        self.assertEqual(git(self.site, "log", "-1", "--format=%an <%ae>"),
                         "github-actions[bot] <41898282+github-actions[bot]@users.noreply.github.com>")
        self.assertEqual(git(self.site, "log", "-1", "--format=%s"), "tools: preview test")

    def test_second_run_with_same_content_changes_nothing(self):
        if not self.page.exists():
            self.skipTest("tool/index.html is absent")
        self.assertEqual(self.run_script().returncode, 0)
        self.out.write_text("")
        proc = self.run_script()
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        text = self.out.read_text()
        self.assertIn("changed=false", text)
        self.assertIn(f"previous_commit={self.src_commit}", text)

    def test_site_without_vendored_directory_is_skipped(self):
        bare = Path(self.tmp) / "bare-site"
        bare.mkdir()
        git(bare, "init", "-q", "-b", "main")
        proc = self.run_script(site=bare)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertIn("::warning::", proc.stdout)
        self.assertIn("changed=false", self.out.read_text())
        self.assertFalse((bare / "assets").exists())

    def test_source_commit_must_match_checkout(self):
        proc = self.run_script(SOURCE_COMMIT="0" * 40)
        self.assertNotEqual(proc.returncode, 0)


if __name__ == "__main__":
    unittest.main()
