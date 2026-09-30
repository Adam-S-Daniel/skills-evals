#!/usr/bin/env python3
"""ADR 0004 — the scheduled eval runs on the roster its own run just merged.

Adam's decision of 2026-09-30: "Remove the need for me to approve roster
changes and have the roster update occur immediately before evals run."
`roster-pr` now publishes and arms the roster pull request BEFORE the `eval`
job; a new `roster-wait` job waits (bounded) for that pull request to merge
and verifies the merge; the `eval` job overlays the ONE merged file,
`evals/roster.yml`, onto its own `$GITHUB_SHA` checkout, and otherwise runs
on the committed roster exactly as before and says why.

Everything here parses `.github/workflows/eval.yml` with PyYAML (never a
regex over its text) and runs the real step scripts it pulls out of the
parsed document, against a fake `gh` answered from a REAL local git
repository and a fake-free `git` — no network, no sleeps (the wait step's
interval is injected as 0), no wall clock.

Discovered and run by test/run_tests.py; also runnable on its own with
`python3 test/issues/test_issue_eval_on_merged_roster.py`.
"""

from __future__ import annotations

import base64
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import yaml

TEST_DIR = Path(__file__).resolve().parent.parent
REPO_ROOT = TEST_DIR.parent
EVAL_WORKFLOW = REPO_ROOT / ".github" / "workflows" / "eval.yml"

REPO = "example/skills-evals"
WAIT_STEP = "Wait for the armed roster pull request to merge"
SWEEP_STEP = "Disarm the roster pull request unless it merged"
OVERLAY_STEP = "Use the roster this run merged, or the committed one"

HAVE_TOOLS = all(shutil.which(t) for t in ("bash", "git", "jq"))

OLD_ROSTER = b"arms:\n  - id: claude-old\njudge:\n  id: claude-judge\n"
NEW_ROSTER = b"arms:\n  - id: claude-new\njudge:\n  id: claude-judge\n"


def _doc():
    return yaml.safe_load(EVAL_WORKFLOW.read_text(encoding="utf-8"))


def _needs(job):
    needs = job.get("needs") or []
    return sorted([needs] if isinstance(needs, str) else needs)


def _step(job, name):
    return next(s for s in job["steps"] if s.get("name") == name)


def _ancestors(jobs, name):
    seen, stack = set(), list(_needs(jobs[name]))
    while stack:
        cur = stack.pop()
        if cur not in seen:
            seen.add(cur)
            stack.extend(_needs(jobs[cur]))
    return seen


def _git(cwd, *args, check=True):
    return subprocess.run(["git", "-C", str(cwd), "-c", "user.name=t",
                           "-c", "user.email=t@example.com", *args],
                          capture_output=True, text=True, check=check)


def _parse_output(path: Path) -> dict:
    out = {}
    if not path.exists():
        return out
    for line in path.read_text(encoding="utf-8").splitlines():
        key, sep, value = line.partition("=")
        if sep:
            out[key] = value
    return out


#: A fake `gh`, answered from real git in `$FAKE_GIT_DIR`. The pull
#: request's own state is a test-controlled SEQUENCE (`$FAKE_PR_STATES`, one
#: JSON object per poll, the last one repeated), because "is it merged yet"
#: is not something a local repository can answer. Its files list is REAL:
#: `git diff --name-status base...head` of the state last served. Every call
#: is logged to `$FAKE_GH_LOG`; any call whose argument line contains
#: `$FAKE_GH_FAIL` fails with a bare HTTP status, the way `gh` does.
FAKE_GH = r'''
import base64
import json
import os
import subprocess
import sys

args = sys.argv[1:]
line = " ".join(args)
with open(os.environ["FAKE_GH_LOG"], "a", encoding="utf-8") as handle:
    handle.write(line + "\n")
fail = os.environ.get("FAKE_GH_FAIL", "")
if fail and fail in line:
    sys.stderr.write("HTTP 502\n")
    raise SystemExit(1)
gitdir = os.environ.get("FAKE_GIT_DIR", "")


def git(*a):
    done = subprocess.run(["git", "-C", gitdir, *a], capture_output=True)
    if done.returncode:
        raise SystemExit(1)
    return done.stdout


def answer(obj, jq):
    text = json.dumps(obj)
    if jq:
        done = subprocess.run(["jq", "-r", jq], input=text, capture_output=True, text=True)
        sys.stdout.write(done.stdout)
        raise SystemExit(done.returncode)
    print(text)
    raise SystemExit(0)


def states():
    with open(os.environ["FAKE_PR_STATES"], encoding="utf-8") as handle:
        return json.load(handle)


def last_state():
    counter = os.environ["FAKE_PR_STATES"] + ".served"
    served = int(open(counter).read()) if os.path.exists(counter) else 0
    seq = states()
    return seq[min(max(served, 1), len(seq)) - 1]


if args[:1] == ["api"]:
    url, jq = args[1], None
    if "--jq" in args:
        jq = args[args.index("--jq") + 1]
    path = url.split("/", 3)[3]
    if path.startswith("pulls/") and path.count("/") == 1:
        counter = os.environ["FAKE_PR_STATES"] + ".served"
        served = int(open(counter).read()) if os.path.exists(counter) else 0
        seq = states()
        state = seq[min(served, len(seq) - 1)]
        with open(counter, "w") as handle:
            handle.write(str(served + 1))
        if state == "error":
            sys.stderr.write("HTTP 502\n")
            raise SystemExit(1)
        answer(state, jq)
    if path.startswith("pulls/") and "/files" in path:
        state = last_state()
        rng = "%s...%s" % (state["base"]["sha"], state["head"]["sha"])
        names = {"A": "added", "M": "modified", "D": "removed"}
        files = []
        for row in git("diff", "--name-status", rng).decode().splitlines():
            code, _, name = row.partition("\t")
            files.append({"filename": name, "status": names.get(code[:1], code)})
        answer(files, jq)
    if path.startswith("contents/evals/roster.yml?ref="):
        ref = path.split("?ref=", 1)[1]
        data = git("show", ref + ":evals/roster.yml")
        # GitHub wraps the base64 at 60 columns; so does this stand-in.
        enc = base64.encodebytes(data).decode()
        answer({"content": enc, "encoding": "base64"}, jq)
    if path == "git/ref/heads/main":
        answer({"object": {"sha": git("rev-parse", "main").decode().strip()}}, jq)
    if path.startswith("compare/"):
        base, head = path[len("compare/"):].split("...")
        if base == head:
            status = "identical"
        elif subprocess.run(["git", "-C", gitdir, "merge-base", "--is-ancestor", base, head]).returncode == 0:
            status = "ahead"
        elif subprocess.run(["git", "-C", gitdir, "merge-base", "--is-ancestor", head, base]).returncode == 0:
            status = "behind"
        else:
            status = "diverged"
        answer({"status": status}, jq)
    if path.startswith("pulls?state=open"):
        rows_file = os.environ.get("FAKE_PR_ROWS", "")
        rows = json.load(open(rows_file)) if rows_file and os.path.exists(rows_file) else []
        answer(rows, jq)
    sys.stderr.write("HTTP 404\n")
    raise SystemExit(1)
if args[:2] == ["pr", "merge"]:
    raise SystemExit(0)
sys.stderr.write("unexpected gh call\n")
raise SystemExit(1)
'''


class _Scripts(unittest.TestCase):
    """The parsed workflow and a scratch directory per test."""

    def setUp(self):
        self.doc = _doc()
        self.jobs = self.doc["jobs"]
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)


# --- the job graph --------------------------------------------------------


class TestTheJobGraph(_Scripts):
    """The new order: roster -> disarm -> roster-pr (publish + arm) ->
    roster-wait -> eval -> publish. Asserted on the parsed `needs:`."""

    def test_the_jobs_are_exactly_these_six(self):
        self.assertEqual(sorted(self.jobs),
                         ["disarm", "eval", "publish", "roster", "roster-pr", "roster-wait"])

    def test_each_jobs_needs(self):
        self.assertEqual(_needs(self.jobs["roster"]), [])
        self.assertEqual(_needs(self.jobs["disarm"]), ["roster"])
        # ADR 0004: `roster-pr` arms BEFORE the eval, so it no longer needs
        # `eval` or `publish`; `disarm` must finish first, or it would turn
        # off the auto-merge this job just enabled.
        self.assertEqual(_needs(self.jobs["roster-pr"]), ["disarm", "roster"])
        self.assertEqual(_needs(self.jobs["roster-wait"]), ["roster", "roster-pr"])
        self.assertEqual(_needs(self.jobs["eval"]),
                         ["disarm", "roster", "roster-pr", "roster-wait"])
        self.assertEqual(_needs(self.jobs["publish"]), ["eval", "roster"])

    def test_the_agent_starts_only_after_the_wait_resolved(self):
        # Invariant 3: nothing armed while the agent runs. `eval` needs the
        # wait job directly, and the wait job comes after the arming job.
        self.assertIn("roster-wait", _needs(self.jobs["eval"]))
        self.assertIn("roster-pr", _ancestors(self.jobs, "roster-wait"))
        self.assertIn("disarm", _ancestors(self.jobs, "roster-pr"))

    def test_no_contents_write_job_can_run_while_a_pr_is_armed(self):
        # Invariant 2: every job holding `contents: write` (or the App
        # token) either finishes before `roster-pr` arms, or starts only
        # after `roster-wait` resolved the arming (merged or disarmed).
        for name, job in self.jobs.items():
            perms = job.get("permissions") or {}
            if perms.get("contents") != "write" or name == "roster-pr":
                continue
            with self.subTest(job=name):
                self.assertIn("roster-wait", _ancestors(self.jobs, name),
                              f"`{name}` holds contents: write and could run "
                              "beside an armed roster pull request")
        # Nothing depends on `publish`, and `roster-pr` depends on no job
        # that runs after it.
        for name, job in self.jobs.items():
            with self.subTest(job=name):
                self.assertNotIn("publish", _needs(job))
        self.assertFalse({"eval", "publish", "roster-wait"} & _ancestors(self.jobs, "roster-pr"))

    def test_the_gates(self):
        self.assertEqual(self.jobs["roster-pr"].get("if"),
                         "${{ !cancelled() && github.ref == 'refs/heads/main' }}")
        # Invariants 7 and 8: no wait on a `roster_only` dispatch or off `main`.
        self.assertEqual(self.jobs["roster-wait"].get("if"),
                         "${{ !cancelled() && github.ref == 'refs/heads/main' "
                         "&& !inputs.roster_only }}")
        # A failed or skipped wait never blocks the eval: it runs on the
        # committed roster instead.
        self.assertEqual(self.jobs["eval"].get("if"),
                         "${{ !cancelled() && !inputs.roster_only }}")


class TestTheWaitJobsShape(_Scripts):
    """Invariant 10: read-only polling with GITHUB_TOKEN, `pull-requests:
    write` only for the disarm; bounded, with timeouts above the cap."""

    def setUp(self):
        super().setUp()
        self.job = self.jobs["roster-wait"]

    def test_permissions_are_exactly_these(self):
        self.assertEqual(self.job.get("permissions"),
                         {"pull-requests": "write", "contents": "read"})

    def test_steps_and_their_gates(self):
        self.assertEqual([s.get("name") for s in self.job["steps"]], [WAIT_STEP, SWEEP_STEP])
        wait = _step(self.job, WAIT_STEP)
        sweep = _step(self.job, SWEEP_STEP)
        self.assertEqual(wait.get("id"), "wait")
        # The disarm runs whatever happened to the wait step — failed,
        # timed out or cancelled — so a timed-out wait still disarms.
        self.assertEqual(sweep.get("if"), "${{ always() }}")
        for step in (wait, sweep):
            self.assertNotIn("uses", step, "no third-party action in this job")
            self.assertNotIn("${{", step["run"])
            self.assertEqual(step["env"].get("GH_TOKEN"), "${{ github.token }}")

    def test_no_checkout_and_no_app_token(self):
        text = json.dumps(self.job)
        for marker in ("actions/checkout", "ROSTER_APP", "secrets.", "vars.", "run_eval.py"):
            self.assertNotIn(marker, text)

    def test_outputs_come_from_the_wait_step(self):
        self.assertEqual(self.job.get("outputs"), {
            "roster_source": "${{ steps.wait.outputs.roster_source }}",
            "roster_reason": "${{ steps.wait.outputs.roster_reason }}",
            "merge_sha": "${{ steps.wait.outputs.merge_sha }}",
            "pr_number": "${{ steps.wait.outputs.pr_number }}",
        })

    def test_inputs_arrive_through_env(self):
        env = _step(self.job, WAIT_STEP)["env"]
        self.assertEqual(env.get("ARMED"), "${{ needs.roster-pr.outputs.armed }}")
        self.assertEqual(env.get("PR_NUMBER"), "${{ needs.roster-pr.outputs.pr_number }}")
        self.assertEqual(env.get("PUSHED_SHA"), "${{ needs.roster-pr.outputs.pushed_sha }}")
        self.assertEqual(env.get("PROPOSED_ROSTER_B64"),
                         "${{ needs.roster.outputs.proposed_roster_b64 }}")
        self.assertEqual(env.get("REPO"), "${{ github.repository }}")
        # The interval and cap are NOT set by the workflow: production takes
        # the script's own defaults, and only a test injects them.
        self.assertNotIn("ROSTER_WAIT_INTERVAL_SECONDS", env)
        self.assertNotIn("ROSTER_WAIT_MAX_POLLS", env)

    @unittest.skipUnless(HAVE_TOOLS, "needs bash, git and jq")
    def test_the_default_cap_fits_inside_the_step_and_job_timeouts(self):
        # The script prints its effective bound before anything else; read
        # the DEFAULTS from a run that injects nothing.
        run = _step(self.job, WAIT_STEP)["run"]
        done = subprocess.run(["bash", "-c", run], capture_output=True, text=True, timeout=60,
                              env={"PATH": os.environ["PATH"], "RUNNER_TEMP": str(self.tmp),
                                   "REPO": REPO, "ARMED": ""})
        self.assertEqual(done.returncode, 0, done.stderr)
        first = done.stdout.splitlines()[0]
        self.assertTrue(first.startswith("roster wait: up to "), first)
        words = first.split()
        polls, interval = int(words[4]), int(words[7])
        cap_minutes = polls * interval / 60
        step_timeout = _step(self.job, WAIT_STEP)["timeout-minutes"]
        # `test` takes ~7-12 min on CI; the cap leaves margin above that,
        # and both timeouts sit above the cap so the script — not a kill —
        # ends the wait, and the disarm step still has room to run.
        self.assertGreaterEqual(cap_minutes, 25)
        self.assertLess(cap_minutes, step_timeout)
        self.assertLess(step_timeout, self.job["timeout-minutes"])


class TestRosterPrStillHoldsTheAppTokenAlone(_Scripts):
    """Invariant 1 and 4 under the new order."""

    def test_only_roster_pr_mentions_the_app(self):
        for name, job in self.jobs.items():
            if name == "roster-pr":
                continue
            text = json.dumps(job)
            for marker in ("ROSTER_APP", "create-github-app-token", "secrets.", "vars."):
                with self.subTest(job=name, marker=marker):
                    self.assertNotIn(marker, text)

    def test_roster_pr_publishes_its_arming_as_outputs(self):
        job = self.jobs["roster-pr"]
        manage = _step(job, "Manage the roster pull request")
        self.assertEqual(manage.get("id"), "manage")
        self.assertEqual(job.get("outputs"), {
            "armed": "${{ steps.manage.outputs.armed }}",
            "pr_number": "${{ steps.manage.outputs.pr_number }}",
            "pushed_sha": "${{ steps.manage.outputs.pushed_sha }}",
        })
        # It runs before the eval now, so it can no longer read the eval's
        # result.
        self.assertNotIn("needs.eval", json.dumps(job))

    def test_the_eval_job_gets_no_token_and_no_write_scope(self):
        job = self.jobs["eval"]
        self.assertEqual(job["permissions"], {"contents": "read", "id-token": "write"})
        overlay = _step(job, OVERLAY_STEP)
        self.assertNotIn("${{", overlay["run"])
        for key, value in (overlay.get("env") or {}).items():
            self.assertNotIn("TOKEN", key.upper())
            self.assertNotIn("github.token", str(value))
            self.assertNotIn("secrets.", str(value))

    def test_the_overlay_runs_before_anything_reads_the_roster(self):
        names = [s.get("name") for s in self.jobs["eval"]["steps"]]
        overlay = names.index(OVERLAY_STEP)
        self.assertEqual(names[overlay - 1], "Check out skills-evals")
        self.assertLess(overlay, names.index("WIF auth preflight"))
        self.assertLess(overlay, names.index("Run the eval (both arms, judge)"))
        step = _step(self.jobs["eval"], OVERLAY_STEP)
        self.assertEqual(step.get("working-directory"), "skills-evals")
        self.assertEqual(step["env"], {
            "ROSTER_SOURCE": "${{ needs.roster-wait.outputs.roster_source }}",
            "ROSTER_REASON": "${{ needs.roster-wait.outputs.roster_reason }}",
            "MERGE_SHA": "${{ needs.roster-wait.outputs.merge_sha }}",
            "ROSTER_PR_NUMBER": "${{ needs.roster-wait.outputs.pr_number }}",
            "PROPOSED_ROSTER_B64": "${{ needs.roster.outputs.proposed_roster_b64 }}",
        })


# --- the wait step, run ----------------------------------------------------


class _Origin(_Scripts):
    """A real repository standing in for GitHub's copy of skills-evals:
    `main` at A (the run's `$GITHUB_SHA`), the proposal commit P on
    `roster/proposal`, and — per test — a merge commit M on `main`."""

    def setUp(self):
        super().setUp()
        self.origin = self.tmp / "origin"
        subprocess.run(["git", "-c", "init.defaultBranch=main", "init", "-q",
                        str(self.origin)], check=True)
        (self.origin / "evals").mkdir()
        (self.origin / "evals" / "roster.yml").write_bytes(OLD_ROSTER)
        (self.origin / "README.md").write_text("x\n", encoding="utf-8")
        _git(self.origin, "add", "-A")
        _git(self.origin, "commit", "-q", "-m", "A")
        self.a = self._rev("main")

    def _rev(self, ref):
        return _git(self.origin, "rev-parse", ref).stdout.strip()

    def _propose(self, content=NEW_ROSTER, extra=None):
        """P: one commit on `roster/proposal` off A."""
        _git(self.origin, "checkout", "-q", "-b", "roster/proposal", self.a)
        (self.origin / "evals" / "roster.yml").write_bytes(content)
        for name, text in (extra or {}).items():
            (self.origin / name).write_text(text, encoding="utf-8")
        _git(self.origin, "add", "-A")
        _git(self.origin, "commit", "-q", "-m", "roster: proposed model roster (run 1)")
        _git(self.origin, "checkout", "-q", "main")
        self.p = self._rev("roster/proposal")
        return self.p

    def _merge(self, onto="main"):
        """M: `--no-ff` merge of P, as the ruleset's merge-commit-only
        policy lands it."""
        if onto != "main":
            _git(self.origin, "checkout", "-q", "-b", onto, self.a)
        else:
            _git(self.origin, "checkout", "-q", "main")
        _git(self.origin, "merge", "-q", "--no-ff", "-m", "Merge roster", "roster/proposal")
        m = self._rev("HEAD")
        _git(self.origin, "checkout", "-q", "main")
        return m

    def _state(self, *, merged=False, state="open", merge_sha=None, head=None,
               ref="roster/proposal", repo=REPO, base="main", auto=True, number=55):
        return {"number": number, "state": "closed" if merged else state,
                "merged": merged, "merge_commit_sha": merge_sha,
                "head": {"sha": head or self.p, "ref": ref, "repo": {"full_name": repo}},
                "base": {"ref": base, "sha": self.a},
                "auto_merge": {"merge_method": "merge"} if auto else None}


class _WaitHarness(_Origin):

    def _run_wait(self, states, *, armed="true", pr="55", pushed=None,
                  proposal=NEW_ROSTER, polls="3", fail=None, extra_env=None):
        bin_dir = self.tmp / "bin"
        bin_dir.mkdir(exist_ok=True)
        gh = bin_dir / "gh"
        gh.write_text(f"#!{sys.executable}\n" + FAKE_GH, encoding="utf-8")
        gh.chmod(0o755)
        states_file = self.tmp / "states.json"
        states_file.write_text(json.dumps(states), encoding="utf-8")
        (self.tmp / "states.json.served").unlink(missing_ok=True)
        self.log = self.tmp / "gh.log"
        self.log.unlink(missing_ok=True)
        self.output = self.tmp / "github-output"
        self.output.write_text("", encoding="utf-8")
        self.summary = self.tmp / "summary.md"
        self.summary.write_text("", encoding="utf-8")
        runner = self.tmp / "runner"
        runner.mkdir(exist_ok=True)
        env = {"PATH": f"{bin_dir}{os.pathsep}{os.environ['PATH']}",
               "RUNNER_TEMP": str(runner), "GITHUB_OUTPUT": str(self.output),
               "GITHUB_STEP_SUMMARY": str(self.summary),
               "GH_TOKEN": "t", "GITHUB_TOKEN": "t", "REPO": REPO,
               "ARMED": armed, "PR_NUMBER": pr,
               "PUSHED_SHA": self.p if pushed is None else pushed,
               "PROPOSED_ROSTER_B64": base64.b64encode(proposal).decode(),
               "ROSTER_WAIT_INTERVAL_SECONDS": "0", "ROSTER_WAIT_MAX_POLLS": polls,
               "FAKE_GH_LOG": str(self.log), "FAKE_GIT_DIR": str(self.origin),
               "FAKE_PR_STATES": str(states_file),
               "FAKE_PR_ROWS": str(self.tmp / "rows.json")}
        if fail:
            env["FAKE_GH_FAIL"] = fail
        env.update(extra_env or {})
        self.env = env
        run = _step(self.jobs["roster-wait"], WAIT_STEP)["run"]
        done = subprocess.run(["bash", "-c", run], capture_output=True, text=True,
                              timeout=120, env=env, cwd=self.tmp)
        self.assertEqual(done.returncode, 0, done.stderr)
        self.stdout = done.stdout
        return _parse_output(self.output)

    def _run_sweep(self, rows, fail=None):
        (self.tmp / "rows.json").write_text(json.dumps(rows), encoding="utf-8")
        env = dict(self.env)
        env.pop("FAKE_GH_FAIL", None)
        if fail:
            env["FAKE_GH_FAIL"] = fail
        self.log.unlink(missing_ok=True)
        run = _step(self.jobs["roster-wait"], SWEEP_STEP)["run"]
        done = subprocess.run(["bash", "-c", run], capture_output=True, text=True,
                              timeout=60, env=env, cwd=self.tmp)
        self.assertEqual(done.returncode, 0, done.stderr)
        return done.stdout, self._calls()

    def _calls(self):
        return self.log.read_text(encoding="utf-8").splitlines() if self.log.exists() else []

    def _polls(self):
        return [c for c in self._calls() if c == f"api repos/{REPO}/pulls/55"]


@unittest.skipUnless(HAVE_TOOLS, "needs bash, git and jq")
class TestTheWaitStep(_WaitHarness):

    def test_a_verified_merge_is_reported_with_its_merge_commit(self):
        self._propose()
        m = self._merge()
        out = self._run_wait([self._state(), self._state(merged=True, merge_sha=m)])
        self.assertEqual(out.get("roster_source"), "merged")
        self.assertEqual(out.get("roster_reason"), "merged")
        self.assertEqual(out.get("merge_sha"), m)
        self.assertEqual(out.get("pr_number"), "55")
        self.assertEqual(len(self._polls()), 2, self._calls())
        self.assertIn("merged", self.summary.read_text(encoding="utf-8"))

    def test_a_merge_that_touched_another_path_is_refused(self):
        self._propose(extra={"README.md": "planted\n"})
        m = self._merge()
        out = self._run_wait([self._state(merged=True, merge_sha=m)])
        self.assertEqual(out.get("roster_source"), "committed")
        self.assertEqual(out.get("roster_reason"), "verify-failed")
        self.assertNotIn("merge_sha", out)
        self.assertIn("::warning::", self.stdout)

    def test_a_merged_file_that_differs_from_this_runs_proposal_is_refused(self):
        self._propose(content=NEW_ROSTER + b"# edited after the run rendered it\n")
        m = self._merge()
        out = self._run_wait([self._state(merged=True, merge_sha=m)])
        self.assertEqual(out.get("roster_source"), "committed")
        self.assertEqual(out.get("roster_reason"), "verify-failed")
        self.assertNotIn("merge_sha", out)

    def test_a_merge_commit_that_is_not_on_main_is_refused(self):
        self._propose()
        m = self._merge(onto="elsewhere")
        out = self._run_wait([self._state(merged=True, merge_sha=m)])
        self.assertEqual(out.get("roster_reason"), "verify-failed")

    def test_a_merged_pr_whose_head_is_not_the_armed_commit_is_refused(self):
        self._propose()
        m = self._merge()
        out = self._run_wait([self._state(merged=True, merge_sha=m, head=self.a)])
        self.assertEqual(out.get("roster_source"), "committed")
        self.assertEqual(out.get("roster_reason"), "head-moved")

    def test_the_verification_calls_fail_closed(self):
        self._propose()
        m = self._merge()
        for fail in ("/files", "contents/evals/roster.yml", "git/ref/heads/main", "compare/"):
            with self.subTest(fail=fail):
                out = self._run_wait([self._state(merged=True, merge_sha=m)], fail=fail)
                self.assertEqual(out.get("roster_source"), "committed")
                self.assertEqual(out.get("roster_reason"), "verify-failed")

    def test_no_merge_within_the_cap_is_a_timeout_after_exactly_the_cap(self):
        self._propose()
        out = self._run_wait([self._state()], polls="4")
        self.assertEqual(out.get("roster_source"), "committed")
        self.assertEqual(out.get("roster_reason"), "timeout")
        self.assertEqual(len(self._polls()), 4)
        # Polling is read-only: the wait step itself never writes.
        self.assertFalse([c for c in self._calls() if c.startswith("pr ")])

    def test_a_read_error_is_retried_within_the_cap(self):
        self._propose()
        m = self._merge()
        out = self._run_wait(["error", self._state(merged=True, merge_sha=m)])
        self.assertEqual(out.get("roster_source"), "merged")
        self.assertEqual(len(self._polls()), 2)

    def test_terminal_states_stop_the_wait_at_once(self):
        self._propose()
        cases = {
            "closed": self._state(state="closed"),
            "auto-merge-off": self._state(auto=False),
            "head-moved": self._state(head=self.a),
            "identity": self._state(ref="some/other"),
        }
        for reason, state in cases.items():
            with self.subTest(reason=reason):
                out = self._run_wait([state, self._state()], polls="5")
                self.assertEqual(out.get("roster_source"), "committed")
                self.assertEqual(out.get("roster_reason"), reason)
                self.assertEqual(len(self._polls()), 1)
        for label, state in (("fork", self._state(repo="someone/skills-evals")),
                             ("other base", self._state(base="release"))):
            with self.subTest(case=label):
                out = self._run_wait([state])
                self.assertEqual(out.get("roster_reason"), "identity")

    def test_nothing_armed_means_no_poll_at_all(self):
        self._propose()
        for armed in ("", "false", "TRUE", "true\n"):
            with self.subTest(armed=armed):
                out = self._run_wait([self._state()], armed=armed)
                self.assertEqual(out.get("roster_source"), "committed")
                self.assertEqual(out.get("roster_reason"), "not-armed")
                self.assertEqual(self._calls(), [])

    def test_hostile_inputs_are_refused_before_any_call(self):
        self._propose()
        for label, kwargs in (("pr number", {"pr": "55; x"}),
                              ("empty pr", {"pr": ""}),
                              ("pushed sha", {"pushed": "main"}),
                              ("proposal", {"proposal": b""})):
            with self.subTest(case=label):
                out = self._run_wait([self._state()], **kwargs)
                self.assertEqual(out.get("roster_source"), "committed")
                self.assertEqual(out.get("roster_reason"), "invalid-input")
                self.assertEqual(self._calls(), [])

    def test_the_default_bound_is_used_when_the_injected_one_is_junk(self):
        self._propose()
        self._run_wait([self._state(merged=True, merge_sha=self._merge())],
                       extra_env={"ROSTER_WAIT_MAX_POLLS": "3x",
                                  "ROSTER_WAIT_INTERVAL_SECONDS": "0"})
        self.assertIn("roster wait: up to 60 polls", self.stdout)


@unittest.skipUnless(HAVE_TOOLS, "needs bash, git and jq")
class TestTheDisarmStep(_WaitHarness):
    """The `always()` step after the wait: whatever the wait decided, any
    open roster pull request's auto-merge is off before the eval starts."""

    OWN = {"number": 55, "head": {"repo": {"full_name": REPO}, "ref": "roster/proposal"}}
    FOREIGN = {"number": 99, "head": {"repo": {"full_name": "someone/skills-evals"},
                                      "ref": "roster/proposal"}}

    def test_a_timeout_disarms_the_open_pr(self):
        self._propose()
        self._run_wait([self._state()], polls="2")
        out, calls = self._run_sweep([self.FOREIGN, self.OWN])
        self.assertEqual([c for c in calls if c.startswith("pr merge")],
                         [f"pr merge 55 --repo {REPO} --disable-auto"])

    def test_after_a_merge_there_is_nothing_open_to_disarm(self):
        self._propose()
        m = self._merge()
        self._run_wait([self._state(merged=True, merge_sha=m)])
        out, calls = self._run_sweep([])
        self.assertEqual([c for c in calls if c.startswith("pr merge")], [])
        self.assertIn("no open roster pull request", out)

    def test_a_failed_disarm_or_lookup_warns_and_exits_zero(self):
        self._propose()
        self._run_wait([self._state()], polls="1")
        out, _ = self._run_sweep([self.OWN], fail="--disable-auto")
        self.assertIn("::warning::could not disable auto-merge for the roster pull request", out)
        out, _ = self._run_sweep([self.OWN], fail="pulls?state=open")
        self.assertIn("::warning::could not find the roster pull request to disarm", out)


# --- the overlay step, run --------------------------------------------------


class _OverlayHarness(_Origin):
    """The `eval` job's checkout: a clone of `origin` at A — its
    `$GITHUB_SHA` — with no credential, exactly as `persist-credentials:
    false` leaves it. The merge lands on `origin` AFTER the clone, so the
    overlay step has to fetch it."""

    def setUp(self):
        super().setUp()
        self.checkout = self.tmp / "skills-evals"
        subprocess.run(["git", "clone", "-q", str(self.origin), str(self.checkout)], check=True)
        self.head = _git(self.checkout, "rev-parse", "HEAD").stdout.strip()

    def _run_overlay(self, *, source="merged", reason="merged", merge_sha="",
                     pr="55", proposal=NEW_ROSTER):
        self.summary = self.tmp / "summary.md"
        self.summary.write_text("", encoding="utf-8")
        runner = self.tmp / "runner"
        runner.mkdir(exist_ok=True)
        env = {"PATH": os.environ["PATH"], "RUNNER_TEMP": str(runner),
               "GITHUB_STEP_SUMMARY": str(self.summary),
               "HOME": str(self.tmp), "GIT_CONFIG_NOSYSTEM": "1",
               "ROSTER_SOURCE": source, "ROSTER_REASON": reason, "MERGE_SHA": merge_sha,
               "ROSTER_PR_NUMBER": pr,
               "PROPOSED_ROSTER_B64": base64.b64encode(proposal).decode()}
        run = _step(self.jobs["eval"], OVERLAY_STEP)["run"]
        done = subprocess.run(["bash", "-c", run], capture_output=True, text=True,
                              timeout=60, env=env, cwd=self.checkout)
        self.assertEqual(done.returncode, 0, done.stderr)
        self.stdout = done.stdout
        return (self.checkout / "evals" / "roster.yml").read_bytes()

    def _only_the_roster_changed(self):
        status = _git(self.checkout, "status", "--porcelain").stdout.splitlines()
        self.assertEqual(status, [" M evals/roster.yml"])
        self.assertEqual(_git(self.checkout, "rev-parse", "HEAD").stdout.strip(), self.head,
                         "the code stays at $GITHUB_SHA; only the roster data moves")

    def _unchanged(self):
        self.assertEqual((self.checkout / "evals" / "roster.yml").read_bytes(), OLD_ROSTER)
        self.assertEqual(_git(self.checkout, "status", "--porcelain").stdout, "")


@unittest.skipUnless(HAVE_TOOLS, "needs bash, git and jq")
class TestTheOverlayStep(_OverlayHarness):

    def test_a_verified_merge_overlays_exactly_the_one_file(self):
        self._propose()
        # `main` also moved for an unrelated reason before the merge: the
        # overlay must not bring that change into the eval's code.
        (self.origin / "README.md").write_text("moved on\n", encoding="utf-8")
        _git(self.origin, "commit", "-q", "-am", "unrelated")
        m = self._merge()
        roster = self._run_overlay(merge_sha=m)
        self.assertEqual(roster, NEW_ROSTER)
        self._only_the_roster_changed()
        self.assertEqual((self.checkout / "README.md").read_text(encoding="utf-8"), "x\n")
        summary = self.summary.read_text(encoding="utf-8")
        self.assertIn("pull request #55", summary)
        self.assertIn(m, summary)

    def test_a_merged_file_that_differs_from_the_proposal_is_refused(self):
        self._propose(content=NEW_ROSTER + b"# planted\n")
        m = self._merge()
        self._run_overlay(merge_sha=m)
        self._unchanged()
        self.assertIn("::warning::", self.stdout)
        self.assertIn("committed `evals/roster.yml`", self.summary.read_text(encoding="utf-8"))

    def test_a_merge_that_touched_another_path_is_refused(self):
        self._propose(extra={"README.md": "planted\n"})
        m = self._merge()
        self._run_overlay(merge_sha=m)
        self._unchanged()
        self.assertIn("::warning::", self.stdout)

    def test_a_merge_not_descended_from_this_runs_commit_is_refused(self):
        # A commit that does not have $GITHUB_SHA in its history cannot be
        # "this run's merge onto main".
        _git(self.origin, "checkout", "-q", "--orphan", "stray")
        (self.origin / "evals" / "roster.yml").write_bytes(NEW_ROSTER)
        _git(self.origin, "add", "-A")
        _git(self.origin, "commit", "-q", "-m", "stray base")
        _git(self.origin, "checkout", "-q", "-b", "stray2")
        (self.origin / "evals" / "roster.yml").write_bytes(OLD_ROSTER)
        _git(self.origin, "commit", "-q", "-am", "x")
        _git(self.origin, "checkout", "-q", "stray")
        _git(self.origin, "merge", "-q", "--no-ff", "-m", "m", "stray2")
        bad = self._rev("HEAD")
        _git(self.origin, "checkout", "-q", "main")
        self._run_overlay(merge_sha=bad, proposal=OLD_ROSTER)
        self._unchanged()
        self.assertIn("::warning::", self.stdout)

    def test_an_unfetchable_or_malformed_merge_sha_is_refused(self):
        for sha in ("0" * 40, "main", "", "A" * 40):
            with self.subTest(sha=sha):
                self._run_overlay(merge_sha=sha)
                self._unchanged()
                self.assertIn("::warning::", self.stdout)

    def test_every_non_merged_outcome_runs_on_the_committed_roster_and_says_why(self):
        self._propose()
        m = self._merge()
        for reason in ("not-armed", "timeout", "closed", "auto-merge-off", "head-moved",
                       "identity", "verify-failed", "invalid-input", "", "junk; rm -rf"):
            with self.subTest(reason=reason):
                # Even a valid merge sha is ignored unless the source says
                # merged.
                self._run_overlay(source="committed", reason=reason, merge_sha=m)
                self._unchanged()
                summary = self.summary.read_text(encoding="utf-8")
                self.assertIn("committed `evals/roster.yml`", summary)
                self.assertNotIn("junk", summary)
        self._run_overlay(source="", reason="", merge_sha="")
        self.assertIn("did not run", self.summary.read_text(encoding="utf-8"))


@unittest.skipUnless(HAVE_TOOLS, "needs bash, git and jq")
class TestTimeoutDisarmsThenTheEvalUsesTheCommittedRoster(_OverlayHarness, _WaitHarness):
    """The whole fallback chain on one history: the wait times out, the
    disarm step turns the armed PR's auto-merge off, and the overlay step
    — fed the wait job's outputs exactly as `needs.roster-wait.outputs.*`
    would carry them — leaves the committed roster in place."""

    def test_timeout_then_disarm_then_committed(self):
        self._propose()
        out = self._run_wait([self._state()], polls="2")
        self.assertEqual(out.get("roster_reason"), "timeout")
        _, calls = self._run_sweep([TestTheDisarmStep.OWN])
        self.assertIn(f"pr merge 55 --repo {REPO} --disable-auto", calls)
        self._run_overlay(source=out.get("roster_source", ""),
                          reason=out.get("roster_reason", ""),
                          merge_sha=out.get("merge_sha", ""), pr=out.get("pr_number", ""))
        self._unchanged()
        self.assertIn("did not merge within", self.summary.read_text(encoding="utf-8"))

    def test_merged_then_overlay_end_to_end(self):
        self._propose()
        m = self._merge()
        out = self._run_wait([self._state(), self._state(merged=True, merge_sha=m)])
        self._run_overlay(source=out["roster_source"], reason=out["roster_reason"],
                          merge_sha=out["merge_sha"], pr=out["pr_number"])
        self.assertEqual((self.checkout / "evals" / "roster.yml").read_bytes(), NEW_ROSTER)
        self._only_the_roster_changed()


if __name__ == "__main__":
    unittest.main()
