#!/usr/bin/env python3
"""Mutation suite for the propagation probes.

Hermetic: no real `claude`, no registry checkout, no network, no wall clock.
`CLAUDE_BIN` points at `test/fake-claude-init`, which SIMULATES skill
resolution (it really reads `$HOME/.claude/skills`, the project's
`.claude/skills` and `installed_plugins.json`) rather than replaying a canned
answer, so the arms exercise their real code path.

The contract every test here is written to: **an assertion nobody has watched
fail is not an assertion.** Each mutation names the exact clause it breaks and
asserts the SPECIFIC verdict and exit code that must result — "it fails
somehow" is satisfied by a probe that fails on everything, which is why
`test_unmutated_run_passes_every_arm` sits alongside them and requires exit 0
across the board on unmutated fixtures.

Run: python3 test/test_propagation.py
"""

from __future__ import annotations

import collections
import contextlib
import fnmatch
import io
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock

TEST_DIR = Path(__file__).resolve().parent
REPO_ROOT = TEST_DIR.parent
HARNESS_DIR = REPO_ROOT / "harness"
FAKE_CLAUDE_INIT = TEST_DIR / "fake-claude-init"
FAKE_HOOK = TEST_DIR / "fixtures" / "fake-skills-bootstrap.sh"
GOLDEN_STREAM = TEST_DIR / "fixtures" / "init-stream-2.1.231.jsonl"
EVAL_DIR = REPO_ROOT / "evals" / "propagation"

sys.path.insert(0, str(HARNESS_DIR))
import run_account_audit  # noqa: E402
import run_account_drift_issue  # noqa: E402
import run_propagation  # noqa: E402
from propagation import account_store, arms, init_probe  # noqa: E402

NOW = datetime(2026, 8, 14, 12, 0, 0, tzinfo=timezone.utc)
# The arms build their child's environment from init_probe's allowlist, which is
# exactly what would otherwise stop a mutation mode reaching the stub — leaving
# every mutation test silently unmutated and green. Tests widen the allowlist by
# these names only; `test_extra_passthrough_is_empty_in_production` asserts the
# committed value is empty.
STUB_VARS = ("FAKE_INIT_MODE", "FAKE_INIT_DROP", "FAKE_INIT_EXTRA",
             "FAKE_INIT_ACCOUNT", "FAKE_HOOK_MODE")
FIXTURE_SKILLS = ("fixture-alpha", "fixture-beta")


def write_skill(directory: Path, name: str, description: str, body: str = "body\n",
                *, crlf: bool = False, extra: dict | None = None) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    text = f"---\nname: {name}\ndescription: {description}\n---\n{body}"
    (directory / "SKILL.md").write_bytes(
        text.replace("\n", "\r\n").encode() if crlf else text.encode())
    for relpath, content in (extra or {}).items():
        path = directory / relpath
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    return directory


def make_registry(root: Path, bundle: str = "adam",
                  skills=FIXTURE_SKILLS) -> Path:
    """A miniature agentskills checkout, plus a skills.lock whose digests are
    computed from the tree it ships — so the lock can never rot against it."""
    registry = root / "registry"
    for name in skills:
        write_skill(registry / "plugins" / bundle / "skills" / name,
                    name, f"fixture skill {name}.")
    lock = {"registry": "example/agentskills", "ref": "0" * 40,
            "bundles": [bundle],
            "skills": {f"{bundle}/{name}": arms.digest_skill_dir(
                registry / "plugins" / bundle / "skills" / name) for name in skills}}
    (registry / "skills.lock").write_text(json.dumps(lock, indent=2), encoding="utf-8")
    shutil.copy(FAKE_HOOK, registry / "hook.sh")
    return registry


class ProbePrimitiveTests(unittest.TestCase):
    """The stream parser. Every trap here was measured on CLI 2.1.231."""

    def _probe(self, mode="simulate", *, env_extra=None, seed=(), plugins=None):
        root = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, root, ignore_errors=True)
        scratch = arms.make_scratch(root, "leg")
        for name in seed:
            write_skill(scratch.home / ".claude" / "skills" / name, name, "x")
        env = {"FAKE_INIT_MODE": mode, **(env_extra or {})}
        with mock.patch.dict(os.environ,
                                      {"CLAUDE_BIN": str(FAKE_CLAUDE_INIT)}):
            return init_probe.probe(cwd=scratch.ws, home=scratch.home,
                                    tmpdir=scratch.tmp, env_extra=env, timeout=60)

    def test_selects_init_by_type_and_subtype_not_by_index(self):
        # The real prefix: active_goal, autocompact_state, commands_changed x2,
        # THEN init. A parser taking line 0, or the first `type == "system"`,
        # gets commands_changed — which has no `skills` key at all.
        facts = self._probe(seed=["fixture-alpha"])
        self.assertEqual(facts.init_index, 4)
        self.assertEqual(facts.events[:3],
                         [("active_goal", None), ("autocompact_state", None),
                          ("system", "commands_changed")])
        self.assertIn("fixture-alpha", facts.skills)

    def test_golden_stream_first_system_event_has_no_skills(self):
        # Asserted against the committed capture of a REAL run, so the claim
        # survives this stub being rewritten.
        events = [json.loads(line) for line in
                  GOLDEN_STREAM.read_text(encoding="utf-8").splitlines() if line.strip()]
        first_system = next(e for e in events if e.get("type") == "system")
        self.assertEqual(first_system["subtype"], "commands_changed")
        self.assertNotIn("skills", first_system)
        init = next(e for e in events if e.get("subtype") == "init")
        self.assertEqual(events.index(init), 4)

    def test_init_at_index_zero_also_works(self):
        # Same CLI build, scrubbed environment: init is the FIRST line.
        facts = self._probe("index-zero", seed=["fixture-alpha"])
        self.assertEqual(facts.init_index, 0)
        self.assertIn("fixture-alpha", facts.skills)

    def test_no_init_event_is_a_probe_fault(self):
        with self.assertRaises(init_probe.ProbeError) as caught:
            self._probe("no-init")
        self.assertIn("no system/init event", str(caught.exception))

    def test_absent_skills_key_is_a_fault_not_zero_skills(self):
        with self.assertRaises(init_probe.ProbeError) as caught:
            self._probe("no-skills-key")
        self.assertIn("no `skills` LIST", str(caught.exception))

    def test_skills_not_a_list_is_a_fault(self):
        with self.assertRaises(init_probe.ProbeError) as caught:
            self._probe("skills-not-list")
        self.assertIn("no `skills` LIST", str(caught.exception))

    def test_crashed_cli_is_a_probe_fault(self):
        with self.assertRaises(init_probe.ProbeError):
            self._probe("crash")

    def test_string_bait_matches_nothing(self):
        # Permanently blocks a refactor to a regex over the stream: the literal
        # `"skills": ["adam:fixture-alpha"]` sits in another event's STRING
        # field. json.loads + a (type, subtype) select cannot see it.
        facts = self._probe("string-bait")
        self.assertNotIn("adam:fixture-alpha", facts.skills)
        self.assertEqual(facts.skills, ["fixture-builtin-a", "fixture-builtin-b"])

    def test_unparseable_lines_are_counted_never_pattern_matched(self):
        facts = self._probe("garbage-lines", seed=["fixture-alpha"])
        self.assertEqual(facts.unparseable_lines, 1)
        self.assertIn("fixture-alpha", facts.skills)

    def test_duplicate_names_survive(self):
        # Measured on the real CLI: the same skill in ~/.claude/skills and in
        # the project's .claude/skills is listed TWICE. A probe that returned a
        # set would silently lose that.
        root = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, root, ignore_errors=True)
        scratch = arms.make_scratch(root, "dup")
        write_skill(scratch.home / ".claude" / "skills" / "dup", "dup", "personal")
        write_skill(scratch.ws / ".claude" / "skills" / "dup", "dup", "project")
        with mock.patch.dict(os.environ,
                                      {"CLAUDE_BIN": str(FAKE_CLAUDE_INIT)}):
            facts = init_probe.probe(cwd=scratch.ws, home=scratch.home,
                                     tmpdir=scratch.tmp, timeout=60)
        self.assertEqual(facts.skill_counts()["dup"], 2)

    def test_env_is_an_allowlist_not_the_ambient_environment(self):
        # The measured leak: inheriting the ambient environment re-synced 17
        # account skills into a scratch HOME (35 skills vs 16). Popping
        # CLAUDE_CODE_SYNC_SKILLS alone did not stop it.
        with mock.patch.dict(os.environ, {
                "CLAUDE_CODE_REMOTE_SESSION_ID": "s", "CLAUDE_CODE_ENTRYPOINT": "remote",
                "CLAUDE_CODE_SYNC_SKILLS": "1", "SOME_OTHER": "x"}):
            env = init_probe.build_env(home=Path("/h"), tmpdir=Path("/t"))
        for leaked in ("CLAUDE_CODE_REMOTE_SESSION_ID", "CLAUDE_CODE_ENTRYPOINT",
                       "CLAUDE_CODE_SYNC_SKILLS", "SOME_OTHER"):
            self.assertNotIn(leaked, env)
        self.assertEqual(env["ANTHROPIC_BASE_URL"], init_probe.BLACKHOLE_BASE_URL)

    def test_credentials_are_never_passed_through(self):
        with mock.patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-x"}):
            env = init_probe.build_env(home=Path("/h"), tmpdir=Path("/t"),
                                       extra={"ANTHROPIC_AUTH_TOKEN": "oat"})
        self.assertNotIn("ANTHROPIC_API_KEY", env)
        self.assertNotIn("ANTHROPIC_AUTH_TOKEN", env)

    def test_scope_flags_are_refused_unless_declared(self):
        root = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, root, ignore_errors=True)
        scratch = arms.make_scratch(root, "scope")
        with self.assertRaises(init_probe.ProbeError) as caught:
            init_probe.probe(cwd=scratch.ws, home=scratch.home, tmpdir=scratch.tmp,
                             extra_argv=["--setting-sources", "project"])
        self.assertIn("--setting-sources", str(caught.exception))

    def test_arms_declare_no_scope_flags(self):
        # `--setting-sources project` drops user-level skills (35 -> 18 when
        # measured), so an arm acquiring one silently measures a different
        # surface than the one it names.
        source = (HARNESS_DIR / "propagation" / "arms.py").read_text(encoding="utf-8")
        for flag in init_probe.SCOPE_FLAGS:
            self.assertNotIn(f'"{flag}"', source)


class ChannelAttributionTests(unittest.TestCase):
    def _facts(self, skills, commands=None):
        return init_probe.ProbeFacts(
            init={"skills": skills}, commands=commands or {},
            commands_seen=bool(commands))

    def test_namespace_means_plugin(self):
        self.assertEqual(init_probe.attribute(self._facts(["adam:x"]))["adam:x"],
                         "plugin")

    def test_sync_suffix_means_account(self):
        facts = self._facts(["y"], {"y": "desc (claude.ai sync)"})
        self.assertEqual(init_probe.attribute(facts)["y"], "account")

    def test_everything_else_is_local(self):
        self.assertEqual(init_probe.attribute(self._facts(["z"]))["z"], "local")

    def test_account_sentinel_is_the_discriminator_that_always_exists(self):
        # commands_changed is NOT emitted on a surface with no account
        # (measured), so the on-disk store is what the guards key on.
        root = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, root, ignore_errors=True)
        facts = init_probe.ProbeFacts(init={"skills": []}, home=root)
        self.assertFalse(facts.account_sentinel_present())
        (root / init_probe.ACCOUNT_SENTINEL).mkdir(parents=True)
        self.assertTrue(facts.account_sentinel_present())


class LockAndDigestTests(unittest.TestCase):
    def test_empty_lock_is_refused(self):
        # A lock expecting nothing can never fail — every arm built on it would
        # pass vacuously.
        root = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, root, ignore_errors=True)
        path = root / "skills.lock"
        path.write_text(json.dumps({"skills": {}}), encoding="utf-8")
        with self.assertRaises(arms.ArmError) as caught:
            arms.load_lock(path)
        self.assertIn("expects nothing", str(caught.exception))

    def test_digest_changes_on_a_one_byte_edit(self):
        root = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, root, ignore_errors=True)
        skill = write_skill(root / "s", "s", "desc")
        before = arms.digest_skill_dir(skill)
        (skill / "SKILL.md").write_text(
            (skill / "SKILL.md").read_text(encoding="utf-8") + "x", encoding="utf-8")
        self.assertNotEqual(before, arms.digest_skill_dir(skill))

    def test_unlabelled_digest_accepts_both_lock_shapes(self):
        # agentskills#87 relabelled lock digests `sha256:<hex>`. Both shapes are
        # live right now — a re-pinned lock carries the label, one that has not
        # been re-pinned yet does not — so the reader must take either.
        bare = "a" * 64
        self.assertEqual(arms.unlabelled_digest("sha256:" + bare), bare)
        self.assertEqual(arms.unlabelled_digest(bare), bare)

    def test_unlabelled_digest_strips_only_the_sha256_label(self):
        # Not a general "drop everything before a colon": a digest labelled with
        # some OTHER algorithm is not silently normalised into agreement with a
        # sha256 one, and the ABSENT sentinel must survive untouched.
        self.assertEqual(arms.unlabelled_digest("md5:" + "a" * 32), "md5:" + "a" * 32)
        self.assertEqual(arms.unlabelled_digest("ABSENT"), "ABSENT")

    def test_digest_matches_the_registry_generator(self):
        # Binds this third copy of the algorithm to agentskills' own. Skipped
        # where no registry is checked out; propagation.yml runs this suite
        # WITH one, and the live plugin arm is the same binding by other means.
        registry = run_propagation.resolve_registry(None)
        generator = registry / "scripts" / "generate_skills_lock.py"
        if not generator.is_file():
            self.skipTest(f"no agentskills checkout at {registry}")
        root = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, root, ignore_errors=True)
        skill = write_skill(root / "s", "s", "desc",
                            extra={"scripts/x.py": "print(1)\n"})
        proc = subprocess.run([sys.executable, str(generator), "--digest", str(skill)],
                              capture_output=True, text=True, timeout=60)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn(arms.digest_skill_dir(skill), proc.stdout)

    def test_hook_verdict_regex_rejects_a_partial_install(self):
        self.assertIsNone(arms.HOOK_OK_RE.match(
            "skills: 8/9 from file:///r@0abcdef — OK"))
        self.assertIsNotNone(arms.HOOK_OK_RE.match(
            "skills: 9/9 from file:///r@0abcdef — OK"))

    def test_hook_skipped_matcher_is_structural_not_exact(self):
        # agentskills 24977ed enriched the decline sentence with an
        # interpolated diagnostic clause; the matcher must accept BOTH the
        # pre-24977ed sentence and the current one, and must still reject
        # anything that changes what the sentence actually asserts.
        declined = arms.hook_declined_for_durable_session
        self.assertTrue(declined(
            "skills: skipped — durable session, "
            "marketplace install is authoritative"))  # old, pre-24977ed
        self.assertTrue(declined(
            "skills: skipped — durable session (entrypoint=unset, no "
            "remote session id), marketplace install is authoritative"))
        self.assertFalse(declined(
            "skills: 9/9 from file:///r@0abcdef — OK"))  # installed, not skipped
        self.assertFalse(declined(
            "skills: skipped — no skills.lock found, "
            "marketplace install is authoritative"))  # a different reason
        self.assertFalse(declined(
            "skills: skipped — durable session (entrypoint=unset, no "
            "remote session id)"))  # missing the marketplace clause


class GuardTests(unittest.TestCase):
    """A guard that did not hold outranks every finding."""

    LOCK = {"skills": {"adam/fixture-alpha": "0" * 64}}

    def _facts(self, home, skills=("fixture-builtin-a",), commands=None):
        return init_probe.ProbeFacts(init={"skills": list(skills)},
                                     commands=commands or {},
                                     commands_seen=bool(commands), home=home)

    def test_guards_hold_on_a_clean_leg(self):
        root = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, root, ignore_errors=True)
        home = root / "home"
        home.mkdir()
        guards = arms.leg_guards("leg", self._facts(home), scratch=root,
                                 declared_env={}, lock=self.LOCK)
        self.assertTrue(all(g.ok for g in guards), [vars(g) for g in guards])

    def test_account_store_reaching_a_leg_trips_a_guard(self):
        # The measured leak, as a mutation: the arm must go INCONCLUSIVE, not
        # green, because every "no account skills" claim it makes is now void.
        root = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, root, ignore_errors=True)
        home = root / "home"
        (home / init_probe.ACCOUNT_SENTINEL).mkdir(parents=True)
        guards = arms.leg_guards("leg", self._facts(home), scratch=root,
                                 declared_env={}, lock=self.LOCK)
        bad = [g for g in guards if not g.ok]
        self.assertEqual([g.name for g in bad], ["leg/account-store-absent"])
        self.assertEqual(arms._finish("a", guards, []).status, arms.INCONCLUSIVE)

    def test_surface_variables_are_not_in_the_allowlist(self):
        # What makes the ambient inheritance structurally impossible: none of
        # the three variables the bootstrap hook keys on can arrive by accident.
        self.assertFalse(set(arms.SURFACE_VARS) & set(init_probe.PASSTHROUGH))

    def test_extra_passthrough_is_empty_in_production(self):
        # A debugging widening must not be committed.
        self.assertEqual(init_probe.EXTRA_PASSTHROUGH, ())

    def test_a_control_leg_that_declares_a_surface_variable_trips_a_guard(self):
        # The headline trap as an ARM-EDIT mutation: a control leg carrying
        # SKILLS_BOOTSTRAP_FORCE arms the hook it exists to watch decline.
        root = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, root, ignore_errors=True)
        home = root / "home"
        home.mkdir()
        guards = arms.leg_guards("control", self._facts(home), scratch=root,
                                 declared_env={"SKILLS_BOOTSTRAP_FORCE": "1"},
                                 lock=self.LOCK, expect_surface=())
        self.assertIn("control/surface-vars", {g.name for g in guards if not g.ok})

    def test_a_forcing_leg_that_lost_its_surface_variable_trips_a_guard(self):
        # The other direction: an arm that stopped forcing quietly becomes a
        # second copy of its own control leg and passes.
        root = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, root, ignore_errors=True)
        home = root / "home"
        home.mkdir()
        guards = arms.leg_guards("arm", self._facts(home), scratch=root,
                                 declared_env={}, lock=self.LOCK,
                                 expect_surface=("SKILLS_BOOTSTRAP_FORCE",))
        self.assertIn("arm/surface-vars", {g.name for g in guards if not g.ok})

    def test_empty_skill_set_trips_the_builtin_floor(self):
        # The arm expecting to find NOTHING is the one most able to pass on a
        # dead CLI. The floor is what stops it.
        root = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, root, ignore_errors=True)
        home = root / "home"
        home.mkdir()
        guards = arms.leg_guards("leg", self._facts(home, skills=()), scratch=root,
                                 declared_env={}, lock=self.LOCK)
        self.assertIn("leg/builtin-floor", {g.name for g in guards if not g.ok})

    def test_a_bad_guard_outranks_a_passing_finding(self):
        guards = [arms.Guard("g", False, "broken")]
        result = arms._finish("arm", guards, [arms.Finding("a", True, "fine")])
        self.assertEqual(result.status, arms.INCONCLUSIVE)
        self.assertIn("guards:", result.render())

    def test_failure_render_always_carries_the_guard_block(self):
        result = arms._finish("arm", [arms.Guard("g", True, "ok")],
                              [arms.Finding("a", False, "nope")])
        self.assertEqual(result.status, arms.FAIL)
        self.assertIn("guards:", result.render())


class DeliveryDifferentialTests(unittest.TestCase):
    def test_exact_set_equality_not_a_count(self):
        # An arm that only checked "more skills than before" would pass on any
        # plugin at all.
        delivered = arms._delivered(
            init_probe.ProbeFacts(init={"skills": ["b"]}),
            init_probe.ProbeFacts(init={"skills": ["b", "x", "y"]}))
        self.assertTrue(arms._delivery_finding({"x", "y"}, delivered, "local").ok)
        self.assertFalse(arms._delivery_finding({"x"}, delivered, "local").ok)

    def test_undeclared_extra_is_a_failure_too(self):
        delivered = arms._delivered(
            init_probe.ProbeFacts(init={"skills": []}),
            init_probe.ProbeFacts(init={"skills": ["x", "rogue"]}))
        finding = arms._delivery_finding({"x"}, delivered, "local")
        self.assertFalse(finding.ok)
        self.assertIn("undeclared extras: ['rogue']", finding.detail)

    def test_missing_skill_is_named(self):
        delivered = arms._delivered(
            init_probe.ProbeFacts(init={"skills": []}),
            init_probe.ProbeFacts(init={"skills": ["x"]}))
        finding = arms._delivery_finding({"x", "y"}, delivered, "plugin")
        self.assertFalse(finding.ok)
        self.assertIn("missing: ['y']", finding.detail)


class ArmMutationTests(unittest.TestCase):
    """Every arm assertion, watched failing against the simulator."""

    def setUp(self):
        self.root = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.root, ignore_errors=True)
        self.registry = make_registry(self.root)
        self.env = mock.patch.dict(
            os.environ, {"CLAUDE_BIN": str(FAKE_CLAUDE_INIT),
                         "FAKE_INIT_MODE": "simulate"})
        self.env.start()
        self.addCleanup(self.env.stop)
        self.seam = mock.patch.object(init_probe, "EXTRA_PASSTHROUGH", STUB_VARS)
        self.seam.start()
        self.addCleanup(self.seam.stop)

    def ctx(self, **overrides):
        run_root = Path(tempfile.mkdtemp(dir=self.root))
        defaults = dict(root=run_root, registry=self.registry,
                        lock_path=self.registry / "skills.lock",
                        lock=arms.load_lock(self.registry / "skills.lock"),
                        hook=self.registry / "hook.sh", bundle="adam",
                        collision_skill="fixture-alpha", timeout=60)
        defaults.update(overrides)
        return arms.ArmContext(**defaults)

    def run_arm(self, name, **overrides):
        return arms.run_arm(name, self.ctx(**overrides))

    def findings(self, result):
        return {f.assertion: f for f in result.findings}

    # --- unmutated ---------------------------------------------------------

    def test_unmutated_run_passes_every_arm(self):
        # The audit's own audit: a probe that failed on everything would
        # satisfy every mutation below. This is what catches it.
        for name in arms.ARMS:
            with self.subTest(arm=name):
                result = self.run_arm(name)
                self.assertEqual(result.status, arms.PASS, result.render())

    # --- clean-room --------------------------------------------------------

    def test_clean_room_fails_when_a_locked_skill_leaks_in(self):
        result = arms.run_arm("clean-room", self.ctx(
            lock=arms.load_lock(self.registry / "skills.lock")))
        self.assertEqual(result.status, arms.PASS)
        with mock.patch.dict(os.environ, {"FAKE_INIT_MODE": "extra-skill",
                                          "FAKE_INIT_EXTRA": "fixture-alpha"}):
            leaked = self.run_arm("clean-room")
        self.assertEqual(leaked.status, arms.FAIL, leaked.render())
        self.assertIn("leaked: ['fixture-alpha']",
                      self.findings(leaked)["clean-room/no-locked-skills"].detail)

    def test_clean_room_fails_when_the_bundle_namespace_is_present(self):
        # Seeding the plugin into the arm's own HOME is not possible from
        # outside, so drive it the way a stale marketplace install would look:
        # a namespaced name in the stream.
        with mock.patch.dict(os.environ, {"FAKE_INIT_MODE": "extra-skill",
                                          "FAKE_INIT_EXTRA": "adam:whatever"}):
            result = self.run_arm("clean-room")
        self.assertEqual(result.status, arms.FAIL, result.render())
        self.assertIn("adam:whatever",
                      self.findings(result)["clean-room/no-lock-namespace"].detail)

    # --- project-mirror ----------------------------------------------------

    def test_project_mirror_fails_when_a_skill_does_not_load(self):
        with mock.patch.dict(os.environ, {"FAKE_INIT_MODE": "drop-one",
                                                   "FAKE_INIT_DROP": "fixture-beta"}):
            result = self.run_arm("project-mirror")
        self.assertEqual(result.status, arms.FAIL, result.render())
        self.assertIn("missing: ['fixture-beta']",
                      self.findings(result)["delivered-set"].detail)

    def test_project_mirror_fails_when_the_registry_lacks_a_locked_skill(self):
        shutil.rmtree(self.registry / "plugins" / "adam" / "skills" / "fixture-beta")
        result = self.run_arm("project-mirror")
        self.assertEqual(result.status, arms.INCONCLUSIVE)
        self.assertIn("fixture-beta", result.error)

    # --- plugin-marketplace ------------------------------------------------

    def test_plugin_arm_fails_on_a_phantom_lock_entry(self):
        # The live --self-test uses exactly this mutation against the real
        # binary: a lock naming a skill the registry does not ship.
        lock = arms.load_lock(self.registry / "skills.lock")
        lock["skills"]["adam/phantom"] = "0" * 64
        result = self.run_arm("plugin-marketplace", lock=lock)
        self.assertEqual(result.status, arms.FAIL, result.render())
        self.assertIn("adam:phantom", self.findings(result)["delivered-set"].detail)

    def test_plugin_arm_fails_when_content_drifts_from_the_lock(self):
        lock = arms.load_lock(self.registry / "skills.lock")
        lock["skills"]["adam/fixture-alpha"] = "f" * 64
        result = self.run_arm("plugin-marketplace", lock=lock)
        self.assertEqual(result.status, arms.FAIL, result.render())
        self.assertIn("adam/fixture-alpha", self.findings(result)["plugin/digest"].detail)

    def test_plugin_arm_passes_against_a_sha256_labelled_lock(self):
        # THE REGRESSION (2026-08-19). agentskills#87 relabelled every lock
        # digest `sha256:<hex>`; this arm compared its own bare-hex computation
        # against the recorded value and all 8 skills failed at once —
        # `got a6f71e6d… want sha256:a6f71e6d…` — with the CONTENT identical.
        # It was red on skills-evals' main, and the suite stayed green because
        # make_registry() writes the lock in the BARE shape only, so no test
        # ever fed this arm the shape production had moved to.
        lock = arms.load_lock(self.registry / "skills.lock")
        lock["skills"] = {k: "sha256:" + v for k, v in lock["skills"].items()}
        result = self.run_arm("plugin-marketplace", lock=lock)
        self.assertEqual(result.status, arms.PASS, result.render())

    def test_plugin_arm_still_catches_drift_under_a_labelled_lock(self):
        # The negative control for the test above: tolerating the label must not
        # tolerate a wrong digest that happens to carry one.
        lock = arms.load_lock(self.registry / "skills.lock")
        lock["skills"] = {k: "sha256:" + v for k, v in lock["skills"].items()}
        lock["skills"]["adam/fixture-alpha"] = "sha256:" + "f" * 64
        result = self.run_arm("plugin-marketplace", lock=lock)
        self.assertEqual(result.status, arms.FAIL, result.render())
        self.assertIn("adam/fixture-alpha", self.findings(result)["plugin/digest"].detail)

    def test_plugin_arm_fails_when_skills_arrive_unnamespaced(self):
        with mock.patch.dict(os.environ,
                                      {"FAKE_INIT_MODE": "bare-instead-of-ns"}):
            result = self.run_arm("plugin-marketplace")
        self.assertEqual(result.status, arms.FAIL, result.render())
        self.assertIn("missing", self.findings(result)["delivered-set"].detail)

    def test_plugin_arm_negative_control_fires_on_a_preinstalled_bundle(self):
        # If a namespaced skill is visible BEFORE the install, the arm is
        # reading someone else's plugin, not its own delivery.
        with mock.patch.dict(os.environ, {"FAKE_INIT_MODE": "extra-skill",
                                          "FAKE_INIT_EXTRA": "adam:preinstalled"}):
            result = self.run_arm("plugin-marketplace")
        self.assertEqual(result.status, arms.FAIL, result.render())
        self.assertIn("before the install",
                      self.findings(result)["plugin/negative-control"].detail)

    def test_an_account_skill_reaching_an_arm_makes_it_inconclusive(self):
        # Not a FAIL: with the account store in play, every "no account skills"
        # claim the arm makes is void, so neither verdict would mean anything.
        with mock.patch.dict(os.environ, {"FAKE_INIT_MODE": "account-leak",
                                          "FAKE_INIT_ACCOUNT": "leaked-from-the-account"}):
            result = self.run_arm("clean-room")
        self.assertEqual(result.status, arms.INCONCLUSIVE, result.render())
        self.assertIn("account-names-absent", result.render())

    # --- bootstrap-hook ----------------------------------------------------

    def test_hook_arm_fails_when_the_surface_guard_does_not_fire(self):
        # The headline trap: a control leg that installs anyway. Without this
        # the "expect nothing" leg passes for entirely the wrong reason.
        with mock.patch.dict(os.environ,
                                      {"FAKE_HOOK_MODE": "ignore-surface-guard"}):
            result = self.run_arm("bootstrap-hook")
        self.assertEqual(result.status, arms.FAIL, result.render())
        self.assertIn("the surface guard did not fire",
                      self.findings(result)["hook/control-installed-nothing"].detail)

    def test_hook_arm_fails_on_a_different_decline_sentence(self):
        # Asserting only "the skills are not visible" would pass here — the
        # hook declined for an unknown reason and said so in words nobody
        # planned for.
        with mock.patch.dict(os.environ, {"FAKE_HOOK_MODE": "wrong-sentence"}):
            result = self.run_arm("bootstrap-hook")
        self.assertEqual(result.status, arms.FAIL, result.render())
        self.assertIn("nothing to do",
                      self.findings(result)["hook/control-verdict"].detail)

    def test_hook_arm_fails_when_the_decline_still_writes_skills(self):
        with mock.patch.dict(os.environ, {"FAKE_HOOK_MODE": "skip-but-install"}):
            result = self.run_arm("bootstrap-hook")
        self.assertEqual(result.status, arms.FAIL, result.render())
        self.assertTrue(self.findings(result)["hook/control-verdict"].ok)
        self.assertFalse(self.findings(result)["hook/control-installed-nothing"].ok)

    def test_hook_arm_fails_on_a_partial_install_verdict(self):
        with mock.patch.dict(os.environ, {"FAKE_HOOK_MODE": "wrong-count"}):
            result = self.run_arm("bootstrap-hook")
        self.assertEqual(result.status, arms.FAIL, result.render())
        self.assertFalse(self.findings(result)["hook/verdict"].ok)

    def test_hook_arm_fails_when_a_skill_does_not_load_after_install(self):
        with mock.patch.dict(os.environ, {"FAKE_INIT_MODE": "drop-one",
                                                   "FAKE_INIT_DROP": "fixture-alpha"}):
            result = self.run_arm("bootstrap-hook")
        self.assertEqual(result.status, arms.FAIL, result.render())
        self.assertIn("missing: ['fixture-alpha']",
                      self.findings(result)["delivered-set"].detail)

    # --- collision-guard ---------------------------------------------------

    def test_collision_arm_fails_when_the_hook_copies_anyway(self):
        # The message alone would pass: the hook says it skipped and copies.
        with mock.patch.dict(os.environ,
                                      {"FAKE_HOOK_MODE": "collision-copies-anyway"}):
            result = self.run_arm("collision-guard")
        self.assertEqual(result.status, arms.FAIL, result.render())
        self.assertTrue(self.findings(result)["collision/verdict"].ok)
        self.assertIn("copied it anyway",
                      self.findings(result)["collision/not-written"].detail)

    def test_collision_arm_fails_when_no_collision_is_reported(self):
        result = self.run_arm("collision-guard", collision_skill="not-in-the-lock")
        self.assertEqual(result.status, arms.FAIL, result.render())
        self.assertFalse(self.findings(result)["collision/verdict"].ok)

    # --- probe faults are never assertion failures -------------------------

    def test_a_reused_scratch_root_is_refused(self):
        # The bug this caught in its own harness: a second run under the same
        # root finds the first run's install already in the "clean" HOME, so
        # its control leg measures the previous run. Refusing is the only safe
        # direction — the arm goes INCONCLUSIVE, never quietly FAIL or PASS.
        ctx = self.ctx()
        first = arms.run_arm("clean-room", ctx)
        self.assertEqual(first.status, arms.PASS)
        second = arms.run_arm("clean-room", ctx)
        self.assertEqual(second.status, arms.INCONCLUSIVE, second.render())
        self.assertIn("already exists", second.error)

    def test_self_test_gets_its_own_scratch_root(self):
        # Same bug, at the seam where it actually shipped: the self-test must
        # not inherit the arms' root, or it reports FAIL (and therefore "the
        # assertions still work") because of a stale marketplace install.
        ctx = self.ctx()
        arms.run_arm("plugin-marketplace", ctx)
        seen = []
        real = arms.run_arm

        def capture(name, given):
            seen.append(given)
            return real(name, given)

        with mock.patch.object(arms, "run_arm", capture):
            ok, line = run_propagation.self_test(ctx)
        self.assertTrue(ok, line)
        # It ran somewhere else, and the phantom is what it injected.
        self.assertNotEqual(seen[0].root, ctx.root)
        self.assertIn("adam/phantom-skill", seen[0].lock["skills"])

    def test_a_dead_cli_makes_every_arm_inconclusive_never_green(self):
        with mock.patch.dict(os.environ, {"CLAUDE_BIN": "/bin/false"}):
            for name in arms.ARMS:
                with self.subTest(arm=name):
                    result = self.run_arm(name)
                    self.assertEqual(result.status, arms.INCONCLUSIVE, result.render())


class AccountAuditTests(unittest.TestCase):
    """Tier 3, hermetic: a fake account store against a fake registry."""

    def setUp(self):
        self.root = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.root, ignore_errors=True)
        self.registry = make_registry(self.root, skills=("fixture-alpha",))
        self.home = self.root / "home"
        self.store = self.home / account_store.MANIFEST_RELPATH.parent
        self.store.mkdir(parents=True)
        self.description = "fixture skill fixture-alpha."
        write_skill(self.store / "fixture-alpha", "fixture-alpha", self.description)
        self._manifest(self.description)

    def _manifest(self, description, name="fixture-alpha"):
        (self.store / "manifest.json").write_text(json.dumps({
            "lastUpdated": 0,
            "skills": [{"skillId": name, "name": name, "source": "custom",
                        "description": description,
                        "updatedAt": "2026-05-11T22:23:38.972889Z"}]}),
            encoding="utf-8")

    def audit(self):
        return account_store.audit(self.home, self.registry)

    def test_in_sync_is_a_pass(self):
        result = self.audit()
        self.assertEqual(result.status, "pass", [vars(f) for f in result.findings])
        self.assertEqual(result.checked, ["fixture-alpha"])

    def test_crlf_only_difference_is_not_drift(self):
        # THE mutation that keeps this check alive. Account copies arrive CRLF;
        # the registry is LF. A "stricter" future edit that drops normalisation
        # reintroduces a false positive on every skill, and the check gets muted
        # rather than fixed.
        write_skill(self.store / "fixture-alpha", "fixture-alpha", self.description,
                    crlf=True)
        self.assertEqual(self.audit().status, "pass")

    def test_one_changed_byte_is_drift(self):
        write_skill(self.store / "fixture-alpha", "fixture-alpha", self.description,
                    body="body!\n")
        result = self.audit()
        self.assertEqual([f.kind for f in result.findings], ["content-drift"])

    def test_missing_payload_file_is_named(self):
        # The incident shape: the account copy tells the agent to run a script
        # the upload dropped.
        (self.registry / "plugins" / "adam" / "skills" / "fixture-alpha"
         / "scripts").mkdir(parents=True)
        (self.registry / "plugins" / "adam" / "skills" / "fixture-alpha"
         / "scripts" / "run.py").write_text("print(1)\n", encoding="utf-8")
        kinds = {f.kind for f in self.audit().findings}
        self.assertIn("missing-payload", kinds)

    def test_description_of_record_drift_is_reported(self):
        # Only the description gates invocation, so a stale one is a skill that
        # silently stops triggering while still looking installed. The pair is
        # what the ACCOUNT serves vs what the REGISTRY declares.
        self._manifest("Writing in a voice.")
        result = self.audit()
        self.assertIn("description-drift", {f.kind for f in result.findings})

    def test_an_internally_consistent_but_stale_store_is_still_drift(self):
        # The mutation that catches comparing the wrong pair: the manifest and
        # the account's own SKILL.md agree with each other and BOTH lag the
        # registry. An internal-consistency check passes here; this must not.
        stale = "Writing in a voice."
        self._manifest(stale)
        write_skill(self.store / "fixture-alpha", "fixture-alpha", stale)
        kinds = {f.kind for f in self.audit().findings}
        self.assertIn("description-drift", kinds)
        self.assertIn("content-drift", kinds)

    def test_an_unreadable_registry_copy_does_not_blame_the_account(self):
        (self.registry / "plugins" / "adam" / "skills" / "fixture-alpha"
         / "SKILL.md").write_text("no frontmatter here\n", encoding="utf-8")
        kinds = {f.kind for f in self.audit().findings}
        self.assertIn("registry-description-unreadable", kinds)
        self.assertNotIn("description-drift", kinds)

    def test_unparseable_frontmatter_is_reported(self):
        # Delivered, command-registered, and invisible to the model.
        (self.store / "fixture-alpha" / "SKILL.md").write_text(
            "---\nname: fixture-alpha\ndescription: trigger on: this\n---\nbody\n",
            encoding="utf-8")
        self.assertIn("unparseable-frontmatter",
                      {f.kind for f in self.audit().findings})

    def test_registry_skills_absent_from_the_account_are_not_this_audits_business(self):
        self._manifest("anything", name="not-in-the-registry")
        result = self.audit()
        self.assertEqual(result.checked, [])
        self.assertEqual(result.skipped, ["not-in-the-registry"])

    def test_no_account_store_is_a_fault_never_a_pass(self):
        with self.assertRaises(account_store.AuditError) as caught:
            account_store.audit(self.root / "nowhere", self.registry)
        self.assertIn("no account store", str(caught.exception))

    def test_cli_exit_codes(self):
        def run(*extra):
            return run_account_audit.main(
                ["--registry", str(self.registry), "--home", str(self.home),
                 "--now", "2026-08-14T12:00:00Z", *extra])
        self.assertEqual(run(), 0)
        write_skill(self.store / "fixture-alpha", "fixture-alpha", self.description,
                    body="drifted\n")
        self.assertEqual(run(), 1)
        self.assertEqual(run_account_audit.main(
            ["--registry", str(self.registry), "--home", str(self.root / "nowhere"),
             "--now", "2026-08-14T12:00:00Z"]), 2)

    def test_a_relative_registry_does_not_fabricate_drift(self):
        # The propagation hook bug's class at its second site. `git_tracked`
        # runs `git -C <registry> ls-files -- <skill dir>`, so the CHILD reads
        # that pathspec inside the registry: a relative one lands outside it
        # (measured: rc=128, "is outside repository"), git_tracked returns None,
        # and the comparison falls back to a raw filesystem walk — which counts
        # git-ignored working-tree files as payload the account copy is missing.
        # A relative `--registry` is a legitimate thing for a caller to pass and
        # this test is what guarantees the harness copes with it: the red it
        # would otherwise invent reds the next pull request through the
        # freshness gate. ROUTINE.md passes absolute as well, belt and braces,
        # which is not a substitute for resolving it here. The absolute leg is
        # the control: it proves the ignored file is the only difference, so a
        # green relative leg means "resolved like the absolute one", not "the
        # file was harmless".
        if shutil.which("git") is None:
            self.skipTest("no git here, so the ls-files filter is moot anyway")
        (self.registry / ".gitignore").write_text("*.log\n", encoding="utf-8")
        for argv in (["init", "-q", str(self.registry)],
                     ["-C", str(self.registry), "add", "-A"]):
            self.assertEqual(subprocess.run(["git", *argv], capture_output=True,
                                            timeout=60).returncode, 0, argv)
        (self.registry / "plugins" / "adam" / "skills" / "fixture-alpha"
         / "debug.log").write_text("never uploaded\n", encoding="utf-8")
        workspace = self.root / "workspace"
        workspace.mkdir()
        self.addCleanup(os.chdir, os.getcwd())
        os.chdir(workspace)

        def audit(registry):
            return run_account_audit.main(
                ["--registry", str(registry), "--home", str(self.home),
                 "--now", "2026-08-14T12:00:00Z"])

        relative = Path("..") / self.registry.name
        self.assertFalse(relative.is_absolute(), "the input must stay relative")
        self.assertEqual(audit(self.registry), 0)
        self.assertEqual(audit(relative), 0)

    def test_published_summary_is_deterministic_and_badge_reflects_it(self):
        out = self.root / "out"
        run_account_audit.main(["--registry", str(self.registry),
                                "--home", str(self.home), "--out", str(out),
                                "--badge", str(out / "badge.json"),
                                "--now", "2026-08-14T12:00:00Z"])
        first = (out / "latest.json").read_bytes()
        run_account_audit.main(["--registry", str(self.registry),
                                "--home", str(self.home), "--out", str(out),
                                "--now", "2026-08-14T12:00:00Z"])
        self.assertEqual(first, (out / "latest.json").read_bytes())
        summary = json.loads(first)
        self.assertEqual(summary["status"], "pass")
        self.assertEqual(summary["generated_at"], "2026-08-14T12:00:00Z")
        self.assertEqual(json.loads((out / "badge.json").read_text())["color"], "green")


class FreshnessGateTests(unittest.TestCase):
    """How a human learns that the scheduled Tier-3 probe went red — or died."""

    def verdict(self, summary, *, bootstrapped=True, max_age_days=3):
        return account_store.freshness_verdict(
            summary, now=NOW, max_age_days=max_age_days, bootstrapped=bootstrapped)

    def _summary(self, *, status="pass", days_ago=0.5, findings=()):
        generated = NOW.timestamp() - days_ago * 86400
        return {"status": status, "generated_at":
                datetime.fromtimestamp(generated, timezone.utc)
                .strftime("%Y-%m-%dT%H:%M:%SZ"),
                "checked": ["a"], "findings": list(findings)}

    def test_fresh_and_passing_is_a_pass(self):
        ok, status, _ = self.verdict(self._summary())
        self.assertTrue(ok)
        self.assertEqual(status, "fresh")

    def test_a_routine_that_stopped_firing_reds_the_next_pull_request(self):
        # The single most important line of the design: a scheduled job that
        # silently stops running is otherwise invisible forever.
        #
        # The message must name ALL THREE causes of staleness, because the
        # verdict cannot distinguish them: the Routine stopped; it ran and its
        # result never reached eval-results; or its bound session was replaced
        # by one that cannot push. Blaming the schedule alone sends
        # the reader to check a trigger that is perfectly healthy — 2026-08-14,
        # when three runs fired, measured correctly, and had every push refused.
        ok, status, message = self.verdict(self._summary(days_ago=11))
        self.assertFalse(ok)
        self.assertEqual(status, "stale")
        self.assertIn("stopped firing", message)
        self.assertIn("no longer reaching eval-results", message)
        # Third cause, added after #47: the bound session was silently
        # replaced by a sourceless one, so the Routine fires and measures
        # but can never push. Without this the reader checks a healthy
        # schedule and a healthy branch and finds nothing.
        self.assertIn("no repository sources", message)
        self.assertIn("11.0 days ago", message)
        self.assertIn("limit 3", message)

    def test_a_red_audit_reds_the_next_pull_request(self):
        ok, status, message = self.verdict(
            self._summary(status="fail", findings=[{"skill": "x", "kind": "content-drift"}]))
        self.assertFalse(ok)
        self.assertEqual(status, "reported-failure")
        self.assertIn("'x'", message)

    def test_before_the_first_run_an_absent_result_is_not_a_failure(self):
        # The bootstrap fix. Without it this gate reds every pull request from
        # the day it merges, and gets disabled in week one.
        ok, status, _ = self.verdict(None, bootstrapped=False)
        self.assertTrue(ok)
        self.assertEqual(status, "not-yet-bootstrapped")

    def test_after_the_first_run_a_vanished_result_is_a_failure(self):
        ok, status, _ = self.verdict(None, bootstrapped=True)
        self.assertFalse(ok)
        self.assertEqual(status, "missing")

    def test_an_unreadable_timestamp_is_a_failure_not_a_pass(self):
        ok, status, _ = self.verdict({"status": "pass", "generated_at": "soon"})
        self.assertFalse(ok)
        self.assertEqual(status, "unreadable")


class RunnerTests(unittest.TestCase):
    """The CLI surface: exit codes, and the gate wired to real files."""

    def setUp(self):
        self.root = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.root, ignore_errors=True)
        self.registry = make_registry(self.root)
        self.eval_dir = self.root / "evals" / "propagation"
        self.eval_dir.mkdir(parents=True)
        default_mode = mock.patch.dict(os.environ, {"FAKE_INIT_MODE": "simulate"})
        default_mode.start()
        self.addCleanup(default_mode.stop)
        fixture = (EVAL_DIR / "fixture.yaml").read_text(encoding="utf-8")
        (self.eval_dir / "fixture.yaml").write_text(
            fixture.replace("hook_path: .claude/hooks/skills-bootstrap.sh",
                            "hook_path: hook.sh")
                   .replace("collision_skill: workflow-path-audit",
                            "collision_skill: fixture-alpha"),
            encoding="utf-8")

    def run_cli(self, *extra, registry: Path | None = None):
        # Deliberately does NOT set FAKE_INIT_MODE: a test that selects a
        # mutation must not have it overwritten here. setUp establishes the
        # unmutated default. `registry` defaults to the absolute fixture path;
        # only the relative-path regression below overrides it.
        with mock.patch.dict(os.environ, {"CLAUDE_BIN": str(FAKE_CLAUDE_INIT)}), \
                mock.patch.object(init_probe, "EXTRA_PASSTHROUGH", STUB_VARS):
            return run_propagation.main([str(self.eval_dir), "--registry",
                                         str(self.registry if registry is None
                                             else registry),
                                         "--timeout", "60", *extra])

    def test_all_arms_exit_zero_unmutated(self):
        self.assertEqual(self.run_cli("--no-gate"), 0)

    def test_an_assertion_failure_exits_one(self):
        with mock.patch.dict(os.environ, {"FAKE_INIT_MODE": "drop-one",
                                                   "FAKE_INIT_DROP": "fixture-beta"}):
            self.assertEqual(self.run_cli("--no-gate", "--arm", "project-mirror"), 1)

    def test_a_probe_fault_exits_two_never_one(self):
        with mock.patch.dict(os.environ, {"FAKE_INIT_MODE": "no-init"}):
            self.assertEqual(self.run_cli("--no-gate", "--arm", "clean-room"), 2)

    def test_a_missing_registry_exits_two(self):
        code = run_propagation.main([str(self.eval_dir), "--registry",
                                     str(self.root / "nowhere"), "--no-gate"])
        self.assertEqual(code, 2)

    def test_a_relative_registry_still_finds_the_hook(self):
        # The CI failure, as a mutation of the CALLER rather than the harness:
        # propagation.yml passes `--registry ../agentskills`, and the arms run
        # the hook with `cwd` set to a scratch workspace — so a registry left
        # relative was read against THAT directory and bash could not find the
        # hook (rc=127, "No such file or directory"). Both hook-running arms
        # went INCONCLUSIVE; every local invocation had passed an absolute path,
        # which is why nothing here saw it first.
        #
        # It drives the real runner from a DIFFERENT working directory on
        # purpose. Asserting that resolve_registry() returns an absolute path
        # would be weaker — it still passes if a later edit resolves the path
        # somewhere the cwd has already moved, which is the whole bug.
        workspace = self.root / "workspace"   # CI's layout: a sibling of the
        workspace.mkdir()                     # registry, naming it `../<name>`
        self.addCleanup(os.chdir, os.getcwd())
        os.chdir(workspace)
        relative = Path("..") / self.registry.name
        self.assertFalse(relative.is_absolute(), "the input must stay relative")
        for arm in ("bootstrap-hook", "collision-guard"):  # the two CI reds
            with self.subTest(arm=arm):
                self.assertEqual(
                    self.run_cli("--no-gate", "--arm", arm, registry=relative), 0)

    def test_gate_only_needs_no_cli_at_all(self):
        latest = self.root / "latest.json"
        latest.write_text(json.dumps({
            "status": "pass", "generated_at": "2026-08-14T00:00:00Z",
            "checked": ["a"], "findings": []}), encoding="utf-8")
        with mock.patch.dict(os.environ, {"CLAUDE_BIN": "/bin/false"}):
            code = run_propagation.main([str(self.eval_dir), "--gate-only",
                                         "--account-latest", str(latest),
                                         "--now", "2026-08-14T12:00:00Z"])
        self.assertEqual(code, 0)

    def test_gate_only_fails_on_a_stale_published_result(self):
        latest = self.root / "latest.json"
        latest.write_text(json.dumps({
            "status": "pass", "generated_at": "2026-08-01T00:00:00Z",
            "checked": ["a"], "findings": []}), encoding="utf-8")
        marker = self.root / ".bootstrapped"
        marker.write_text("", encoding="utf-8")
        code = run_propagation.main([str(self.eval_dir), "--gate-only",
                                     "--account-latest", str(latest),
                                     "--account-marker", str(marker),
                                     "--now", "2026-08-14T12:00:00Z"])
        self.assertEqual(code, 1)

    def test_gate_is_silent_before_the_audit_has_ever_published(self):
        code = run_propagation.main([str(self.eval_dir), "--gate-only",
                                     "--account-latest", str(self.root / "absent.json"),
                                     "--account-marker", str(self.root / "absent"),
                                     "--now", "2026-08-14T12:00:00Z"])
        self.assertEqual(code, 0)

    def test_an_unreadable_published_result_fails_the_gate(self):
        latest = self.root / "latest.json"
        latest.write_text("not json", encoding="utf-8")
        code = run_propagation.main([str(self.eval_dir), "--gate-only",
                                     "--account-latest", str(latest),
                                     "--now", "2026-08-14T12:00:00Z"])
        self.assertEqual(code, 1)

    # ---- the account audit's VERDICT is advisory on a pull request ----
    #
    # A red Tier-3 result says the claude.ai account store has drifted. No
    # commit in this repo caused it and none can clear it, so blocking every
    # pull request on it only trains people to ignore the gate while the drift
    # outlives their patience. What must NOT go advisory with it is liveness:
    # a missing, stale or unreadable result means the audit is not reaching us,
    # and catching a Routine that quietly stopped is this gate's whole purpose.

    def _red_audit(self, days_ago=0.5):
        latest = self.root / "latest.json"
        generated = datetime.fromtimestamp(
            datetime(2026, 8, 14, 12, 0, 0, tzinfo=timezone.utc).timestamp()
            - days_ago * 86400, timezone.utc)
        latest.write_text(json.dumps({
            "status": "fail",
            "generated_at": generated.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "checked": ["a"],
            "findings": [{"skill": "drifted-skill", "kind": "content-drift"}],
        }), encoding="utf-8")
        marker = self.root / ".bootstrapped"
        marker.write_text("", encoding="utf-8")
        return latest, marker

    def _gate(self, latest, marker, *extra):
        return run_propagation.main([str(self.eval_dir), "--gate-only",
                                     "--account-latest", str(latest),
                                     "--account-marker", str(marker),
                                     "--now", "2026-08-14T12:00:00Z", *extra])

    def test_the_advisory_set_carries_the_verdict_and_no_liveness_status(self):
        """`run_gate` called directly, because the FLAG only selects this set.

        propagation.yml now asks for the downgrade on every event except the
        schedule, which puts far more traffic through it than the old
        pull-request-only shape did. What keeps that safe is not the workflow:
        it is that `ADVISORY_STATUSES` names `reported-failure` and nothing
        else, so no amount of passing the flag can turn a Routine that stopped
        firing green. Asserted against the set itself rather than only through
        the CLI, so widening it is a red test rather than a quiet policy change
        four events wide.
        """
        self.assertEqual(set(run_propagation.ADVISORY_STATUSES),
                         {"reported-failure"},
                         "only the audit's own verdict may ever be downgraded; "
                         "a liveness status in this set means a dead Routine "
                         "reports green on every surface but the schedule")
        fixture = run_propagation.load_fixture(self.eval_dir)

        latest, marker = self._red_audit()
        ok, line = run_propagation.run_gate(
            fixture, latest, marker, NOW,
            advisory=run_propagation.ADVISORY_STATUSES)
        self.assertTrue(ok)
        # Downgraded, never dropped: the drifted skill is still named, or the
        # run that passes leaves no trace of the drift at all.
        self.assertIn("WARN freshness-gate [reported-failure]", line)
        self.assertIn("drifted-skill", line)

        stale_latest, stale_marker = self._red_audit(days_ago=11)
        ok, line = run_propagation.run_gate(
            fixture, stale_latest, stale_marker, NOW,
            advisory=run_propagation.ADVISORY_STATUSES)
        self.assertFalse(ok)
        self.assertIn("FAIL freshness-gate [stale]", line)

    def test_a_red_audit_still_fails_the_gate_by_default(self):
        # The schedule's path, unchanged: without the flag a red verdict is
        # fatal, which is what makes `report` file the tracking issue.
        latest, marker = self._red_audit()
        self.assertEqual(self._gate(latest, marker), 1)

    def test_a_red_audit_is_advisory_when_asked(self):
        latest, marker = self._red_audit()
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = self._gate(latest, marker, "--account-verdict-advisory")
        self.assertEqual(code, 0)
        out = buf.getvalue()
        # Reported, not swallowed. A downgrade that dropped the line would
        # leave the pull request with no trace of the drift at all.
        self.assertIn("WARN freshness-gate", out)
        self.assertIn("reported-failure", out)
        self.assertIn("drifted-skill", out)

    def test_advisory_does_not_cover_a_routine_that_stopped_firing(self):
        # The one that matters: the flag must not turn the gate off. A stale
        # result is the failure this whole gate exists to surface.
        latest, marker = self._red_audit(days_ago=11)
        self.assertEqual(self._gate(latest, marker), 1)
        self.assertEqual(self._gate(latest, marker,
                                    "--account-verdict-advisory"), 1)

    def test_advisory_does_not_cover_a_vanished_result(self):
        marker = self.root / ".bootstrapped"
        marker.write_text("", encoding="utf-8")
        self.assertEqual(self._gate(self.root / "absent.json", marker,
                                    "--account-verdict-advisory"), 1)

    def test_advisory_does_not_cover_an_unreadable_timestamp(self):
        # Deliberately a READABLE object with an unusable `generated_at`, so
        # this reaches the `unreadable` STATUS. Unparseable JSON returns before
        # the verdict is computed and so cannot exercise the advisory set at
        # all -- writing "not json" here made the test pass no matter what the
        # set contained, which is not a test.
        latest = self.root / "latest.json"
        latest.write_text(json.dumps({"status": "pass", "generated_at": "soon"}),
                          encoding="utf-8")
        marker = self.root / ".bootstrapped"
        marker.write_text("", encoding="utf-8")
        self.assertEqual(self._gate(latest, marker,
                                    "--account-verdict-advisory"), 1)

    def test_advisory_does_not_cover_a_lock_that_is_not_json(self):
        # The earlier return, before any verdict exists. Separate test because
        # it proves a different line.
        latest = self.root / "latest.json"
        latest.write_text("not json", encoding="utf-8")
        marker = self.root / ".bootstrapped"
        marker.write_text("", encoding="utf-8")
        self.assertEqual(self._gate(latest, marker,
                                    "--account-verdict-advisory"), 1)

    def test_run_record_is_written_when_asked(self):
        record = self.root / "record.json"
        self.assertEqual(self.run_cli("--no-gate", "--arm", "clean-room",
                                      "--json", str(record)), 0)
        payload = json.loads(record.read_text(encoding="utf-8"))
        self.assertEqual(payload["arms"][0]["status"], arms.PASS)

    def test_self_test_passes_when_the_arm_can_still_detect_a_bad_lock(self):
        self.assertEqual(self.run_cli("--no-gate", "--arm", "clean-room",
                                      "--self-test"), 0)

    def test_self_test_fails_when_the_arm_stops_detecting_anything(self):
        # The blind spot it exists to close: an arm that can no longer see the
        # difference between a correct lock and a wrong one reports PASS.
        ctx = arms.ArmContext(root=self.root, registry=self.registry,
                              lock_path=self.registry / "skills.lock",
                              lock=arms.load_lock(self.registry / "skills.lock"),
                              hook=self.registry / "hook.sh", bundle="adam",
                              collision_skill="fixture-alpha", timeout=60)
        with mock.patch.object(arms, "run_arm",
                               return_value=arms.ArmResult("plugin-marketplace",
                                                           arms.PASS)):
            ok, line = run_propagation.self_test(ctx)
        self.assertFalse(ok)
        self.assertIn("stopped detecting anything", line)

    def test_unknown_arm_is_a_fault(self):
        self.assertEqual(self.run_cli("--no-gate", "--arm", "nope"), 2)

    def test_committed_fixture_names_only_real_arms(self):
        fixture = run_propagation.load_fixture(EVAL_DIR)
        self.assertTrue(set(fixture["arms"]) <= set(arms.ARMS))
        self.assertEqual(sorted(fixture["arms"]), sorted(arms.ARMS))


class _DryRunStepContract:
    """The shared contract for a scheduled step that files a tracking issue.

    Two workflows here have one — propagation.yml's `report` (the probes are
    failing) and account-store-drift.yml's `react` (the account store has
    drifted). They report different facts to different readers, but the SHAPE
    of the step is the same one, and the shape is what keeps being got wrong.

    A MIXIN rather than a base TestCase, so unittest never collects it on its
    own: a contract class with no workflow bound to it passes by checking
    nothing, which is the failure every guard below is written against. Each
    subclass binds WORKFLOW, JOB, WRITE_SPELLINGS, PROLOGUE_ALLOWLIST and
    `select_step`, and adds whatever its own workflow needs on top.

    It was written for propagation.yml first, and everything below is the
    reason why.

    propagation.yml stays runnable by hand, and its dry run never writes.

    A probe you cannot run on demand is a probe you cannot VERIFY on demand. A
    fix to the arms merged and confirming it meant waiting for a push or the
    05:41 cron, because the dispatch came back `422 Workflow does not have
    'workflow_dispatch' trigger`. Losing the trigger again would be silent —
    nothing red, just a button that is not there on the day someone needs it —
    so it is pinned here rather than left to review.

    The dry run is the other half. `report` is the only place in this repo that
    WRITES anything (gh issue create / comment, the sole `issues: write` grant
    in the workflow); the runner it invokes, `harness/run_propagation.py`, has
    no write path at all. So "dry run" can only mean: run the detection, run
    the dedupe lookup, and stop one line short of the two gh write calls. Two
    ways that silently stops being true — the flag getting built inline as
    `${{ inputs.dry_run && 'x' || 'y' }}`, which is not a ternary and fires its
    `||` branch on any falsy `&&` branch (cms-platform run 32280743541 skipped
    a whole scan that way while printing a healthy result), and a later edit
    moving a write above the bail-out — are what the last three tests exist
    for.

    That last one is guarded twice over, and deliberately from opposite
    directions. The narrow test names the two `gh issue` calls and pins them
    below the bail-out; the allowlist test names nothing that writes at all and
    instead requires every statement ABOVE the bail-out to be a shape known to
    be harmless. The narrow one alone was not enough — a review hoisted
    `gh api -X POST …/issues`, then `curl -X POST`, and it stayed green both
    times, because a denylist of spellings can only catch the spellings
    somebody already listed.

    Everything here goes through a real YAML parser. A line scan cannot see
    which job an `if:` belongs to, and this suite is the one that would have to
    catch that.
    """

    # The one statement above the bail-out that may run a command inside
    # `$( )`, named so the allowlist below and the test can agree on which it
    # is without either of them counting entries.
    DEDUPE_LOOKUP = "the dedupe lookup"

    # Every sequence that can put a SECOND command into one statement. Counted
    # on EVERY prologue statement against the budget its allowlist entry
    # declares, because matching a whole-line pattern is not enough on its own:
    # a pattern ending in `.*` swallows a separator happily, so
    # `echo hi; gh api -X POST …/issues` fullmatches `echo .*` and an
    # adversarial review walked exactly that past an earlier version of this
    # guard. Longest-first so `&&` is not counted as two `&`.
    COMMAND_SEPARATORS = (r"\$\(", r">\(", r"<\(", r"&&", r"\|\|", ";", r"\|", "&", "`")
    SEPARATOR_RE = re.compile("|".join(COMMAND_SEPARATORS))

    def setUp(self):
        import yaml
        # Read outside any try/except: a missing or unparseable workflow must
        # blow up here, not degrade into a test that quietly asserts nothing.
        self.doc = yaml.safe_load(self.WORKFLOW.read_text(encoding="utf-8"))
        # A bare `on:` key is the YAML 1.1 boolean True once parsed.
        self.triggers = self.doc.get("on", self.doc.get(True))
        self.job = self.doc["jobs"][self.JOB]
        # WHICH step gets linted is the subclass's call, and it is an assertion
        # rather than an index. Every step in a job runs under that job's
        # `issues: write` grant, so a job that grows a step this suite does not
        # know about has grown a write path nothing checks — each subclass says
        # below how it rules that out for its own workflow.
        self.step = self.select_step()
        self.assertIn("run", self.step,
                      "the step this suite lints must be the scripted one; "
                      f"found {self.step.get('uses')!r}")

    def _dry_run_env_var(self) -> str:
        """The env name carrying the dispatch input, taken from the workflow.

        Derived rather than hard-coded so a rename cannot leave the shell
        testing one variable while the workflow sets another — which would
        make the dry run a no-op that still passes every other test here.
        """
        wired = {k: v for k, v in (self.step.get("env") or {}).items()
                 if "inputs.dry_run" in str(v)}
        self.assertEqual(len(wired), 1,
                         "exactly one env entry may carry the dry_run input "
                         f"into the step; found {sorted(wired)}")
        return next(iter(wired))

    def test_the_workflow_can_be_dispatched_with_a_dry_run_input(self):
        self.assertIn("workflow_dispatch", self.triggers,
                      "without workflow_dispatch a probe fix cannot be "
                      "verified until the next push or the daily cron")
        inputs = (self.triggers["workflow_dispatch"] or {}).get("inputs") or {}
        self.assertIn("dry_run", inputs,
                      "a dispatch with no dry_run input can only run the probes "
                      "by also arming the tracking-issue write")
        self.assertIs(inputs["dry_run"]["default"], True,
                      "the dispatch defaults to dry — a verification run that "
                      "files a real tracking issue leaves a human tidying up "
                      "after the tool they reached for to save work")

    def test_the_flag_reaches_the_shell_as_a_bare_input_reference(self):
        expr = str(self.step["env"][self._dry_run_env_var()])
        for operator in ("&&", "||"):
            self.assertNotIn(
                operator, expr,
                f"{expr!r} must stay a bare `${{{{ inputs.dry_run }}}}` and the "
                "flag be built in shell. `a && b || c` is not a ternary: GitHub "
                "returns c whenever b is falsy, and an empty string is falsy, "
                "which is how cms-platform shipped an opt-out that fired "
                "unconditionally while reporting a healthy result")

    def test_no_workflow_expression_is_interpolated_into_the_script(self):
        """The fleet rule, and it is not only about the obvious spelling.

        `${{ }}` is substituted into a `run:` body BEFORE the shell sees any of
        it, so the rendered command is echoed into a public log and evaluated
        as shell — which is why every value these steps read arrives through
        `env:` instead. `FreshnessGateEventPolicyTests` already pins that for
        the gate step; the two steps that hold `issues: write` had no such
        assertion, and the gap is not theoretical: a comment added here while
        fixing an unrelated defect explained the rule by QUOTING it, and an
        empty expression in a shell comment is a workflow-level syntax error
        that no test, no shell parse and no reading of the diff caught. GitHub
        does not know `#` starts a comment — it expands the whole block.
        """
        self.assertNotIn(
            "${{", self.step["run"],
            f"the {self.JOB!r} job's scripted step interpolates a workflow "
            "expression into its `run:` body. Values reach the script through "
            "`env:` — including inside comments, which are expanded like every "
            "other line here.")

    def _first(self, lines, predicate, what, after=-1):
        """Index of the first matching line after `after`, or a failure.

        Never returns a sentinel: a missing landmark has to fail loudly here,
        because every ordering assertion built on one is trivially true
        against an index nobody found.
        """
        hits = [i for i, line in enumerate(lines) if i > after and predicate(line)]
        self.assertTrue(hits, f"no {what} in the report step's script")
        return hits[0]

    def _bail_out(self, lines):
        """(index of the `if` guarding the dry run, index of its `exit 0`)."""
        var = self._dry_run_env_var()
        guard = self._first(
            lines, lambda l: l.lstrip().startswith("if ") and f'"${var}"' in l,
            f"shell test on ${var}")
        return guard, self._first(lines, lambda l: l.strip() == "exit 0",
                                  "`exit 0`", after=guard)

    @staticmethod
    def _heredoc_delimiter(text):
        """(delimiter, is the body EXPANDED?) for a heredoc `text` opens, else None.

        Quoting the delimiter is what makes a heredoc body inert. `<<'EOF'`
        is literal; bare `<<EOF` is expanded by the shell, so a `$( )` in the
        body RUNS — which is a command above the dry-run bail-out that the
        body is not obviously carrying. This workflow uses the bare form, so
        the distinction is live and not theoretical, and it is why the
        delimiter's quoting is returned rather than discarded.

        `<<` only opens a heredoc where the SHELL sees it as an operator.
        Inside a quoted string it is ordinary prose, and a scanner that cannot
        tell the difference stops reading the script at the first line that
        merely mentions it. An adversarial review walked a write past this
        guard exactly that way — `echo "if it recurs see << ESCALATION in the
        runbook"` took ESCALATION for a delimiter, every statement after it
        including a bare `gh api -X POST …/issues` became heredoc body, and
        none of them was ever checked. So quoting is tracked here rather than
        approximated: this walks the text, keeps single/double-quote state, and
        only considers a `<<` found outside both.
        """
        in_single = in_double = False
        i = 0
        while i < len(text):
            ch = text[i]
            if ch == "\\" and not in_single:
                i += 2                      # escaped character, quote or not
                continue
            if ch == "'" and not in_double:
                in_single = not in_single
            elif ch == '"' and not in_single:
                in_double = not in_double
            elif ch == "<" and not in_single and not in_double \
                    and text.startswith("<<", i):
                # The quotes around a delimiter must MATCH (`<<'EOF'`, not
                # `<<'EOF`), hence the backreference. `<<<` is a here-string,
                # not a heredoc, and fails this match — keep scanning rather
                # than concluding there is no heredoc on the line.
                found = re.match(r"<<-?\s*([\"']?)([A-Za-z_]\w*)\1", text[i:])
                if found:
                    return found.group(2), not found.group(1)
                i += 2
                continue
            i += 1
        return None

    def _statements(self, lines):
        """[(line index, text, "command" | "heredoc")] for everything the shell EVALUATES.

        Three things stop a line from meaning what it looks like it means, and
        all three are handled here rather than in each assertion. A heredoc
        body is data the shell never executes — `cat > … <<EOF` writes a file
        on the runner — so its prose would otherwise be judged as commands.
        Comments and blanks are not statements. And a backslash continuation
        splits one statement over several lines: the dedupe lookup is three
        lines long, so anything reasoning per-line reads two thirds of it as
        bare fragments.

        Both ways this parse can quietly stop covering the script — ending
        mid-continuation, or ending inside a heredoc that never closed — are
        assertions, not silent truncations. Everything downstream is an
        allowlist, and an allowlist over the statements a broken parse happened
        to reach passes without having checked the ones it did not.
        """
        statements, heredoc, expands, pending = [], None, False, None
        for i, raw in enumerate(lines):
            if heredoc is not None:
                if raw.strip() == heredoc:
                    heredoc, expands = None, False
                elif expands:
                    # Not inert: the delimiter was unquoted, so the shell
                    # expands this line before `cat` ever sees it.
                    statements.append((i, raw.strip(), "heredoc"))
                continue
            line = raw.strip()
            if pending is None:
                if not line or line.startswith("#"):
                    continue
                start, text = i, line
            else:
                start, text = pending[0], f"{pending[1]} {line}"
            if text.endswith("\\"):
                pending = (start, text[:-1].rstrip())
                continue
            pending = None
            opened = self._heredoc_delimiter(text)
            heredoc, expands = opened if opened else (None, False)
            statements.append((start, text, "command"))
        self.assertIsNone(pending,
                          "the report step's script ends inside a backslash "
                          "continuation, so it does not parse — and nothing "
                          "built on that parse can be trusted")
        self.assertIsNone(
            heredoc,
            f"the report step's script opens a heredoc delimited by {heredoc!r} "
            "and never closes it, so everything after that point was read as "
            "data and never checked as a command")
        return statements

    def test_the_issue_writes_sit_below_the_dry_run_bail_out(self):
        lines = self.step["run"].splitlines()
        guard, bail = self._bail_out(lines)

        # Detection first: the dedupe lookup must run in a dry run too, or the
        # dry run proves the flag works and nothing about the search that
        # decides create-vs-comment.
        lookup = self._first(lines, lambda l: "gh issue list" in l, "`gh issue list`")
        self.assertLess(lookup, guard,
                        "the dedupe lookup must run before the dry-run bail-out")

        writes = [i for i, line in enumerate(lines)
                  if any(call in line for call in self.WRITE_SPELLINGS)]
        self.assertEqual(
            len(writes), len(self.WRITE_SPELLINGS),
            f"expected exactly {list(self.WRITE_SPELLINGS)}, one line each; "
            f"found {len(writes)}. This counts literal `gh issue` spellings "
            "and nothing else: a write spelled `gh api`, `curl` or anything "
            "the GitHub CLI grows next is INVISIBLE here. Catching an "
            "arbitrary write is "
            "test_nothing_above_the_dry_run_bail_out_can_write's job — this "
            "test only pins these known calls to their side of the line.")
        for write in writes:
            self.assertGreater(
                write, bail,
                f"script line {write + 1} writes to the tracking issue above the "
                f"dry-run bail-out, so a dry run would write after all: "
                f"{lines[write].strip()!r}")

    def test_nothing_above_the_dry_run_bail_out_can_write(self):
        """The prologue is an ALLOWLIST of readers, not a denylist of writes.

        Its sibling above finds writes by matching the two literal spellings
        `gh issue create` and `gh issue comment`, and an adversarial review
        proved that is the wrong direction — twice. It hoisted
        `gh api -X POST "/repos/$GITHUB_REPOSITORY/issues"` above the bail-out
        and the suite stayed green; it did it again with `curl -X POST` and
        the suite stayed green again. Both are real issue writes; neither is
        spelled "gh issue". A denylist can only ever name the writes somebody
        already thought of, and the write nobody thought of is the whole
        reason this guard exists.

        So this inverts it. Every statement up to and including the dry-run
        `exit 0` must match one of PROLOGUE_ALLOWLIST — a short, stable list
        of shapes that demonstrably cannot reach the tracking issue. Nothing
        in that list names a write, so nothing in it has to be kept in step
        with the vocabulary of the GitHub CLI: `gh api`, `curl`, `wget`,
        `python3 -c`, a third `gh issue create`, all fail identically.

        Two rounds of review then showed that inverting the direction is
        necessary and not sufficient, because BOTH remaining gaps let a write
        reach the tracking issue without ever being compared to the list:

        * A whole-line pattern that ends in `.*` matches a statement with a
          second command bolted onto it, so `echo hi; gh api -X POST …/issues`
          fullmatched `echo .*` and passed. Hence COMMAND_SEPARATORS: what a
          statement may CONTAIN is budgeted per entry, separately from what it
          looks like.
        * A statement that merely mentioned `<<` inside a quoted string made
          the parser treat the rest of the script as heredoc body, so the
          statements after it — a bare `gh api` write among them — were never
          checked at all. Hence the quote-aware `_heredoc_delimiter`, and the
          assertion that a heredoc actually closes.
        * And a heredoc body is only inert when its DELIMITER is quoted. This
          workflow opens `<<EOF` bare, so the shell expands the body: a
          `$(gh api -X POST …/issues)` sitting in the middle of the issue
          prose runs, above the bail-out, while looking like text. Skipping
          bodies wholesale therefore skipped a live command, so an expanded
          body is now read for substitutions and nothing else.

        Both are the same failure in different clothes: the guard examined
        fewer things and said nothing about it. The dedupe-lookup landmark
        below exists for that reason and is asserted before the list is
        applied.

        The cost is a red test the day this step is legitimately rewritten.
        That is the direction the failure should point: widening the allowlist
        is a deliberate line in a diff somebody reads, whereas failing to
        anticipate a spelling is nothing at all.
        """
        lines = self.step["run"].splitlines()
        _, bail = self._bail_out(lines)
        prologue = [entry for entry in self._statements(lines) if entry[0] <= bail]

        # Vacuity control, asserted BEFORE the allowlist is applied: an
        # allowlist run over zero statements passes on every input it never
        # saw, which is precisely the shape of failure this test exists to
        # close. The dedupe lookup is the landmark that proves the parse
        # reached the real script — it is the only statement up here that is
        # neither a shell keyword nor a print, so if the parse collapsed to
        # nothing, or the heredoc scanner swallowed the rest of the file, it
        # is the first thing to go missing.
        lookup_pattern = next(pattern for what, pattern, _ in self.PROLOGUE_ALLOWLIST
                              if what == self.DEDUPE_LOOKUP)
        lookups = [text for _, text, source in prologue
                   if source == "command" and re.fullmatch(lookup_pattern, text)]
        self.assertEqual(
            len(lookups), 1,
            "expected exactly one dedupe lookup above the dry-run bail-out; found "
            f"{len(lookups)} among {len(prologue)} statement(s). Either the script "
            "changed shape or this test parsed something other than it — and an "
            "allowlist with nothing to check passes without checking anything.")

        for start, text, source in prologue:
            where = f"script line {start + 1}"  # of the step's `run:` block, not the file
            if source == "heredoc":
                # The body of a heredoc whose delimiter was NOT quoted. It is
                # not a command, so the allowlist has nothing to say about its
                # shape — but the shell expands it before `cat` receives it,
                # so a substitution in it runs exactly where a command would.
                # Only that is checked; the prose is free to say anything.
                for form in ("$(", "`"):
                    self.assertNotIn(
                        form, text,
                        f"{where} sits in the body of a heredoc opened with an "
                        f"UNQUOTED delimiter, above the dry-run bail-out: {text!r}. "
                        "The shell EXPANDS such a body, so this substitution runs "
                        "on a dry run like any other command. Quote the delimiter "
                        "(`<<\'EOF\'`) if the body is meant to be literal, or move "
                        "the substitution below the bail-out.")
                continue
            allowed = [(what, budget) for what, pattern, budget
                       in self.PROLOGUE_ALLOWLIST if re.fullmatch(pattern, text)]
            self.assertTrue(
                allowed,
                f"{where} runs above the dry-run bail-out and is not one of "
                f"the shapes known not to write: {text!r}. Nothing may run up there "
                "that PROLOGUE_ALLOWLIST does not vouch for — if it genuinely cannot "
                "reach the tracking issue, add it there and say why; if it can, it "
                "belongs below the bail-out with the other writes.")
            what, budget = allowed[0]
            # Matching a shape is necessary and not sufficient. Every allowlist
            # pattern that ends in `.*` will match a statement with a second
            # command bolted onto it, so what a statement is ALLOWED to contain
            # is counted separately from what it looks like: anything over the
            # declared budget is a command this guard never examined.
            found = collections.Counter(self.SEPARATOR_RE.findall(text))
            for sequence, count in sorted(found.items()):
                self.assertLessEqual(
                    count, budget.get(sequence, 0),
                    f"{where} puts {count} {sequence!r} into {what}, above the "
                    f"dry-run bail-out, where {budget.get(sequence, 0)} are "
                    f"accounted for: {text!r}. That is room for a second command "
                    "— a write chained on with `;`, substituted in with `$( )` or "
                    "piped through `>( )` reaches the tracking issue exactly like "
                    "the calls below the bail-out do.")


class DispatchAndDryRunTests(_DryRunStepContract, unittest.TestCase):
    """The contract above, bound to propagation.yml's `report` job."""

    WORKFLOW = REPO_ROOT / ".github" / "workflows" / "propagation.yml"
    JOB = "report"
    # One line each, below the bail-out. `gh issue comment` rather than an
    # edit: this issue is a running log of failing probe runs, unlike the
    # account-drift one, which is a single edited-in-place statement of state.
    # The close call joined them when the job gained a green path. It is a write
    # like the other two, and a write this tuple does not name is one this test
    # never pins to its side of the bail-out — the sibling allowlist test would
    # still refuse to let it sit above there, but nothing would notice it
    # QUIETLY MOVING, which is the failure this narrow test is for.
    WRITE_SPELLINGS = ("gh issue create", "gh issue comment", "gh issue close")

    # (what it is, WHOLE-LINE pattern, separator budget) for every statement
    # shape permitted above the dry-run bail-out. The budget is `{sequence:
    # exact count}` and defaults to none at all: a shape that needs a separator
    # has to say which and how many, so an extra one is a failure even inside a
    # statement whose pattern still matches. Nothing here names a write — that
    # is the entire design; see the test's docstring.
    PROLOGUE_ALLOWLIST = (
        ("shell options", r"set -euo pipefail", {}),
        ("a heredoc into the runner's own temp dir, which is not GitHub",
         r"""cat > "\$RUNNER_TEMP/[\w.-]+" <<(?:'EOF'|EOF)""", {}),
        ("reading that temp file back into the log",
         r'''cat "\$RUNNER_TEMP/[\w.-]+"''', {}),
        # One `$( )` for the substitution itself and one `|` for the jq filter
        # inside it. That budget is what rejects `; gh issue create` chained on
        # the end, and `| tee >(gh api …)` piped into the middle.
        (_DryRunStepContract.DEDUPE_LOOKUP,
         r"number=\$\(gh issue list .*\)", {"$(": 1, "|": 1}),
        # `if gh api …; then` is deliberately NOT this shape: the pattern is
        # anchored on `[` … `]`, and the budget then allows only the one `;`
        # that `]; then` needs.
        ("a `[` test", r"if \[ .* \]; then", {";": 1}),
        ("a shell keyword", r"else", {}),
        ("a shell keyword", r"fi", {}),
        ("a print", r"echo .*", {}),
        ("the bail-out itself", r"exit 0", {}),
    )
    # And the honest boundary, because a guard that claims more than it does is
    # how the test below got written in the first place. This governs the
    # report job's ONE step — `setUp` fails loudly if that job grows a second
    # step of ANY kind, scripted or `uses:`, because a `uses:` step needs no
    # shell to file an issue and would otherwise sit above this script entirely
    # unexamined. It says nothing about any OTHER job: `issues: write` is
    # granted to `report` alone today, but nothing here pins that grant, so a
    # write added under a different job that declared its own is outside this
    # test's reach.
    #
    # NO CREDENTIAL CENSUS HERE, and that is the one-step rule doing the work
    # rather than an omission. The sibling class needs
    # `AccountDriftWorkflowTests._privilege_findings` because its job is six
    # steps under one `issues: write` grant, so "which of them holds a token"
    # is a real question — and its third part refuses a credential declared at
    # `jobs.<id>.env:` or workflow scope, since an inherited `env:` arms every
    # step at once. Neither scope can widen anything HERE: `env:` is inherited
    # by the steps in scope, `report` has exactly one, and that step is the
    # write step, which already declares `GH_TOKEN` legitimately. Measured
    # rather than reasoned about: both splices were run against every test in
    # this class and all 7 stayed OK, which is the correct result and not a
    # gap. What a workflow-level `env:` WOULD reach is `gate` and `arms` — the
    # other jobs, already declared out of scope above, and bounded in fact by
    # the workflow-level `permissions: contents: read` that neither overrides.
    # If `report` ever legitimately needs a second step, the census the
    # sibling class already owns is what has to come with it.

    def select_step(self):
        # EVERY step, not just the scripted ones. Filtering to `run:` steps left
        # a `uses: peter-evans/create-issue-from-file` step able to sit above
        # this script and file the issue with no shell at all — invisible to a
        # guard that only ever reads the script. The report job is one step; if
        # it legitimately needs another, the prologue guard below has to be
        # re-scoped before that lands, which is what this failure says.
        steps = self.job["steps"]
        self.assertEqual(
            len(steps), 1,
            "the report job is expected to be exactly one step; found "
            f"{[s.get('name') or s.get('uses') for s in steps]}. Every step in "
            "this job runs under its `issues: write` grant, and only the "
            "scripted one is checked against the dry-run bail-out.")
        return steps[0]

    def test_the_report_job_is_reachable_on_a_dispatch(self):
        # Otherwise dry_run is a knob wired to nothing: the only job it governs
        # could never run by hand, and the input would read as coverage it is
        # not providing.
        self.assertIn("workflow_dispatch", self.job["if"],
                      "the report job's `if:` must admit workflow_dispatch, or "
                      f"the dry_run input governs nothing: {self.job['if']!r}")

    def test_the_report_job_is_scheduled_on_a_green_run_as_well(self):
        """The close path's precondition, and it is the `if:` and not the shell.

        `failure()` alone is why nothing in this repo ever closed this issue:
        the only job that can write was not scheduled on the run that PROVED
        the probes were healthy again, so a repaired probe left its issue open
        until a person happened to notice. An issue whose presence means "broke
        once" rather than "is broken" is one people stop reading, which is the
        same death as never filing it.

        `always()` is the wrong fix and is refused here: it also fires on a
        CANCELLED upstream job, which measured nothing at all. Closing a live
        finding on the strength of a run that never completed is the one write
        in this step that the next morning's run cannot take back.
        """
        condition = self.job["if"]
        self.assertIn(
            "success()", condition,
            "a green scheduled run must reach the report job or nothing ever "
            f"closes the tracking issue: {condition!r}")
        self.assertIn(
            "failure()", condition,
            f"a red run must still reach it: {condition!r}")
        self.assertNotIn(
            "always()", condition,
            "always() also fires on a cancelled run, which measured nothing: "
            f"closing on it retracts a live finding on no evidence: {condition!r}")


class _StubbedShellStep:
    """Run a workflow step's real `run:` body with the commands it calls stubbed.

    Everything else in this file that reads a workflow reads its SHAPE. That is
    the right instrument for "no write sits above the bail-out", and the wrong
    one for "which flag does this event get" — a script can build an array
    correctly and then never expand it, and a shape test passes on it while
    every event silently takes the same branch. So the two questions that are
    about BEHAVIOUR execute the script instead, with a stub first on `PATH`
    standing in for the one binary it invokes.

    Deterministic in the sense this suite means it: bash, one shell script and
    one file per run. No clock, no network, no CLI, nothing that varies between
    a laptop and a runner.
    """

    @staticmethod
    def _stub(directory: Path, name: str, body: str) -> None:
        path = directory / name
        path.write_text(f"#!/bin/sh\n{body}", encoding="utf-8")
        path.chmod(0o755)

    def _bash(self, script: str, env: dict, stub_dir: Path):
        # A CLOSED environment, not os.environ plus overrides: an ambient
        # GITHUB_* or GH_TOKEN leaking in from the session running the tests
        # would make a `set -u` failure look like a pass, and on a real runner
        # it would be a live credential. PATH is the one thing inherited, and
        # the stub dir goes in front of it.
        proc = subprocess.run(
            ["bash", "-c", script],
            env={"PATH": f"{stub_dir}:{os.environ.get('PATH', '')}", **env},
            capture_output=True, text=True)
        self.assertEqual(
            proc.returncode, 0,
            f"the step's script exited {proc.returncode}: {proc.stderr.strip()}")
        return proc


class FreshnessGateEventPolicyTests(_StubbedShellStep, unittest.TestCase):
    """On WHICH events the account audit's verdict is allowed to fail the run.

    Two separate decisions guard the same downgrade and it is easy to conflate
    them. `ADVISORY_STATUSES` in the runner decides which STATUS may ever be
    downgraded — `reported-failure` and nothing else, so liveness stays fatal
    however this workflow is invoked. What is asserted here is the other half:
    on which EVENT the workflow asks for the downgrade at all. That half lives
    in four lines of shell inside propagation.yml and in no Python this suite
    can import, so those four lines are executed, once per trigger the workflow
    declares.

    The policy changed because the old one was measurably wrong. The flag used
    to be added only on `pull_request`, which left a push to `main` carrying
    the fatal verdict — and a post-merge push has nothing left to block, while
    no commit in this repo can cause or clear claude.ai account-store drift. So
    the red named no action any reader could take, and scheduled-run-health.yml
    then re-reported it as a CI fault: runs 32444343915 and 32445416856
    (2026-08-21) were both such pushes, and both were filed into issue #33. The
    schedule stays fatal because it is the only surface that DOES anything with
    the verdict — `report` files the tracking issue there.

    Iterating the workflow's own trigger list rather than a copy of it is the
    part that keeps working: a trigger added later is tested the day it is
    added, and lands advisory, which is the side that blocks nothing.
    """

    WORKFLOW = REPO_ROOT / ".github" / "workflows" / "propagation.yml"
    FLAG = "--account-verdict-advisory"
    # The only event on which the audit's own verdict may fail the run.
    FATAL_EVENTS = ("schedule",)

    def setUp(self):
        import yaml
        doc = yaml.safe_load(self.WORKFLOW.read_text(encoding="utf-8"))
        self.triggers = doc.get("on", doc.get(True))
        steps = [step for step in doc["jobs"]["gate"]["steps"]
                 if self.FLAG in str(step.get("run") or "")]
        self.assertEqual(
            len(steps), 1,
            "exactly one step in the `gate` job may build the advisory flag; "
            f"found {len(steps)}. A second one is a second policy, and this "
            "test would be linting whichever of them it happened to pick.")
        self.step = steps[0]

    def test_the_event_name_reaches_the_script_through_the_environment(self):
        wired = sorted(name for name, value in (self.step.get("env") or {}).items()
                       if str(value).strip() == "${{ github.event_name }}")
        self.assertEqual(
            wired, ["EVENT_NAME"],
            "the event name must arrive through `env:` under exactly that "
            f"name; found {wired}. The fleet rule is that `${{{{ }}}}` never "
            "goes in a `run:` body, and the test below sets EVENT_NAME to "
            "drive the script — a rename would leave it driving nothing.")
        self.assertNotIn(
            "${{", self.step["run"],
            "no workflow expression may be interpolated into this script: the "
            "rendered command is echoed into a public log and evaluated as "
            "shell")

    def _argv(self, event: str) -> list:
        """The argv this step really hands the runner when `event` fired."""
        stub_dir = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, stub_dir, ignore_errors=True)
        argv_out = stub_dir / "argv"
        # The `\n` is ESCAPED: the stub must be `printf "%s\n" "$@"`. A bare
        # newline inside the format string happens to work in sh and reads like
        # a typo the next person straightens out into something that does not.
        self._stub(stub_dir, "python3",
                   'printf "%s\\n" "$@" > "$ARGV_OUT"\n')
        self._bash(self.step["run"],
                   {"EVENT_NAME": event, "ARGV_OUT": str(argv_out)}, stub_dir)
        # Vacuity control, and it is not theoretical: if the script never
        # reached the runner — a typo, an early `set -e` exit, a stub that did
        # not run — there is no argv, and every "the flag is NOT passed"
        # assertion below would pass without having measured anything at all.
        self.assertTrue(
            argv_out.is_file(),
            f"the gate step's script never invoked python3 on {event!r}, so "
            "there is no invocation to inspect")
        argv = argv_out.read_text(encoding="utf-8").splitlines()
        self.assertIn(
            "--gate-only", argv,
            f"the stub recorded something other than the freshness gate: {argv}")
        return argv

    def test_the_verdict_is_fatal_on_the_schedule_and_advisory_on_every_other_event(self):
        declared = sorted(self.triggers)
        # Named explicitly rather than left to the loop: `push` is the
        # regression this test was written for, and a workflow that quietly
        # lost the trigger would otherwise make its own case vacuous.
        for required in ("pull_request", "push", "schedule"):
            self.assertIn(required, declared,
                          f"propagation.yml no longer declares {required!r}, "
                          "so this policy is being asserted against a workflow "
                          "that cannot exercise it")
        for event in declared:
            with self.subTest(event=event):
                argv = self._argv(event)
                if event in self.FATAL_EVENTS:
                    self.assertNotIn(
                        self.FLAG, argv,
                        f"on {event!r} the audit's verdict must stay FATAL — it "
                        "is the surface where `report` files the tracking "
                        "issue, so a downgrade here means a drifted account "
                        "store is reported to nobody")
                else:
                    self.assertIn(
                        self.FLAG, argv,
                        f"on {event!r} the audit's verdict must be advisory. No "
                        "commit in this repo can cause or clear account-store "
                        "drift, so a red here blocks nothing and names no "
                        "action — runs 32444343915 and 32445416856 were "
                        "exactly that, on `push`, and were re-reported as CI "
                        "faults into issue #33")


class ReportStepBehaviourTests(_StubbedShellStep, unittest.TestCase):
    """What the report step DOES with each pair of job results.

    `DispatchAndDryRunTests` pins where the writes may sit; nothing there says
    which one happens. Both defects this class was written for are behavioural
    and both were invisible to a shape test:

    * the body diagnosed a cause it could not know. It told the reader the
      agentskills registry was the likely culprit, and every scheduled failure
      this workflow has ever had — five of them, run 32452792300 included — was
      the `gate` job on a `[reported-failure]` verdict with all five arms
      green. The body now prints the two job results and describes both halves,
      so the assertions are that the results really reach it and that the
      pointer it offers for a red gate is the drift issue's REAL title.
    * nothing ever closed the issue. A green run reaching the job is one half
      (`test_the_report_job_is_scheduled_on_a_green_run_as_well`); this is the
      other — the script, run with both results green, has to reach the close
      call and not the create one.
    * and then the close reached too far. The `gate` job downgrades the account
      audit's verdict to advisory on every event but the schedule, so the issue
      was opened under a fatal policy and closed under a weaker one: a dispatch
      turned the verdict off, read green, and retracted the finding the 05:41
      run had filed. Which EVENT the step is running under is therefore an
      input to this suite, not ambient context — hence `run_step(event=…)`.

    `gh` is stubbed rather than the whole script paraphrased, so the branch
    under test is the real one, including the dedupe substitution feeding it.
    """

    WORKFLOW = REPO_ROOT / ".github" / "workflows" / "propagation.yml"
    DRIFT_WORKFLOW = ".github/workflows/account-store-drift.yml"

    def setUp(self):
        import yaml
        doc = yaml.safe_load(self.WORKFLOW.read_text(encoding="utf-8"))
        steps = doc["jobs"]["report"]["steps"]
        self.assertEqual(len(steps), 1)
        self.step = steps[0]
        self.temp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.temp, ignore_errors=True)

    def run_step(self, *, gate, arms_result, open_issue="", dry_run="",
                 event="schedule"):
        """(gh calls, stdout, the failure body, the recovery body).

        The stub answers `gh issue list` with `open_issue` — the dedupe lookup
        is a command substitution, so answering it is what selects the
        create-vs-comment branch — and records the first three arguments of
        every other call. Three arguments, not all of them: the close call
        carries a whole issue body in `--comment`, and a log that swallowed it
        would be asserting on prose rather than on which write happened.

        `event` DEFAULTS TO THE SCHEDULE rather than to the empty string, and
        the default is doing work: the schedule is the surface every write here
        is designed for, so the cases below keep meaning what they meant before
        the event became an input. It is a real parameter because the step's
        outcome now depends on it — `_bash` builds a CLOSED environment, so a
        case that forgot to pass one would die on `set -u` rather than quietly
        measuring whichever event the ambient session happened to be running
        under.
        """
        stub_dir = (self.temp /
                    f"stub-{event}-{gate}-{arms_result}-"
                    f"{open_issue or 'none'}-{dry_run or 'live'}")
        stub_dir.mkdir(parents=True)
        runner_temp = stub_dir / "runner-temp"
        runner_temp.mkdir()
        gh_log = stub_dir / "gh.log"
        self._stub(stub_dir, "gh",
                   'if [ "$1" = "issue" ] && [ "$2" = "list" ]; then\n'
                   '  printf "%s" "$GH_OPEN_ISSUE"\n'
                   '  exit 0\n'
                   'fi\n'
                   'printf "%s %s %s\\n" "$1" "$2" "$3" >> "$GH_LOG"\n')
        proc = self._bash(self.step["run"], {
            "RUNNER_TEMP": str(runner_temp),
            "GITHUB_REPOSITORY": "Adam-S-Daniel/skills-evals",
            "ISSUE_TITLE": "Scheduled propagation probes are failing",
            "RUN_URL": "https://example.com/run/1",
            "GATE_RESULT": gate,
            "ARMS_RESULT": arms_result,
            "GITHUB_EVENT_NAME": event,
            "PROBE_DRY_RUN": dry_run,
            "GH_OPEN_ISSUE": open_issue,
            "GH_LOG": str(gh_log),
        }, stub_dir)
        calls = (gh_log.read_text(encoding="utf-8").splitlines()
                 if gh_log.is_file() else [])
        failure = runner_temp / "propagation-failure.md"
        recovered = runner_temp / "propagation-recovered.md"
        # Vacuity control: the bodies are written by the first two statements
        # of the script, so their absence means the run under test stopped
        # before it decided anything and every assertion below is about nothing.
        self.assertTrue(failure.is_file() and recovered.is_file(),
                        "the step's script wrote no body files, so it did not "
                        "run far enough to have taken any branch")
        return (calls, proc.stdout,
                failure.read_text(encoding="utf-8"),
                recovered.read_text(encoding="utf-8"))

    # ---- B1: the body reports which half failed, and diagnoses neither ----

    def test_the_body_carries_both_job_results(self):
        _, _, body, _ = self.run_step(gate="failure", arms_result="success")
        self.assertIn("gate: failure", body)
        self.assertIn("arms: success", body)
        # The other way round too, so this cannot pass on a body that hard-codes
        # the pair the first case happened to use.
        _, _, body, _ = self.run_step(gate="success", arms_result="failure",
                                      open_issue="7")
        self.assertIn("gate: success", body)
        self.assertIn("arms: failure", body)

    def test_a_red_gate_is_pointed_at_the_drift_issue_and_not_at_the_registry(self):
        """The misdiagnosis, as an assertion.

        The title is compared against `run_account_drift_issue.TITLE` rather
        than spelled out again here: that constant is what the drift reactor
        actually files under, and a body naming a title nothing files is a
        reader sent to search for an issue that does not exist. Two copies of
        one identifier is one copy that eventually disagrees, and this is the
        cheap place to find out.
        """
        _, _, body, _ = self.run_step(gate="failure", arms_result="success")
        self.assertIn(run_account_drift_issue.TITLE, body)
        self.assertIn(self.DRIFT_WORKFLOW, body)
        self.assertTrue((REPO_ROOT / self.DRIFT_WORKFLOW).is_file(),
                        "the body points at a workflow that is not in the repo")
        # The registry still gets named — it is the right answer for a red ARM.
        # What must not survive is the old body's claim that it is where to
        # look FIRST regardless of which job went red.
        self.assertIn("agentskills registry", body)

    # ---- B2: which write each pair of results reaches ----

    def test_a_red_run_with_no_open_issue_opens_one(self):
        calls, _, _, _ = self.run_step(gate="failure", arms_result="success")
        self.assertEqual(calls, ["issue create --repo"])

    def test_a_red_run_comments_on_the_issue_already_open(self):
        calls, _, _, _ = self.run_step(gate="failure", arms_result="failure",
                                       open_issue="41")
        self.assertEqual(calls, ["issue comment 41"])

    def test_a_green_run_closes_the_issue_that_is_open(self):
        # The defect this whole path exists for: before it, a repaired probe
        # left its tracking issue open until a human noticed.
        calls, _, _, recovered = self.run_step(gate="success",
                                               arms_result="success",
                                               open_issue="41")
        self.assertEqual(calls, ["issue close 41"])
        self.assertIn("green again", recovered)

    def test_a_green_run_with_nothing_open_writes_nothing(self):
        calls, out, _, _ = self.run_step(gate="success", arms_result="success")
        self.assertEqual(calls, [])
        self.assertIn("no tracking issue is open", out)

    def test_a_green_dispatch_never_closes_the_issue_the_schedule_filed(self):
        """The close is fenced to the event whose verdict is FATAL.

        `gate` passes `--account-verdict-advisory` on every event except the
        schedule, so the two halves of this issue's lifecycle were measured
        under different policies: the 05:41 run reads a `[reported-failure]`
        account verdict, goes red and files the issue, while a dispatch of the
        same commit downgrades that same verdict, comes back green and — before
        this guard — reached `gh issue close`. The dispatch retracted a finding
        it had switched off rather than one it had disproved, and because the
        dedupe lookup is `--state open`, the next morning's schedule filed a
        BRAND-NEW issue instead of finding the closed one: the comment history
        the close path was added to preserve, stranded.

        Driven through the real script rather than read off its shape, because
        a guard can be written correctly and compare the wrong variable —
        which is the same reason `test_a_dry_run_reaches_the_lookup_and_writes_
        nothing` executes rather than greps.
        """
        calls, out, _, _ = self.run_step(gate="success", arms_result="success",
                                         open_issue="51",
                                         event="workflow_dispatch")
        self.assertEqual(
            calls, [],
            "a green workflow_dispatch must write NOTHING: it measured the "
            "account verdict under the advisory policy, so it has not shown "
            "the drift that opened the issue is gone")
        self.assertIn("only a scheduled run may close", out)
        # And the schedule still does close, so the guard cannot pass by
        # fencing the close off from every event including its own.
        calls, _, _, _ = self.run_step(gate="success", arms_result="success",
                                       open_issue="51", event="schedule")
        self.assertEqual(calls, ["issue close 51"])

    def test_a_red_dispatch_still_files_and_still_comments(self):
        # The fence is on the RETRACTION only. A red under the dispatch's
        # weaker policy is red under the schedule's stricter one too, so a
        # dispatch that goes red has found something real and must still be
        # able to say so — fencing the whole job to `schedule` would be the
        # over-correction that makes `dry_run=false` a knob wired to nothing.
        calls, _, _, _ = self.run_step(gate="failure", arms_result="success",
                                       event="workflow_dispatch")
        self.assertEqual(calls, ["issue create --repo"])
        calls, _, _, _ = self.run_step(gate="failure", arms_result="success",
                                       open_issue="51",
                                       event="workflow_dispatch")
        self.assertEqual(calls, ["issue comment 51"])

    def test_a_half_green_run_is_not_a_close(self):
        # `success() || failure()` schedules this job whenever ANY need failed,
        # so both results have to be green before the close call is reached.
        # Testing only the both-green case would pass against a script that
        # closed on `gate` alone and threw away every red arm's report.
        for gate, arms_result in (("success", "failure"), ("failure", "success")):
            with self.subTest(gate=gate, arms=arms_result):
                calls, _, _, _ = self.run_step(gate=gate, arms_result=arms_result,
                                               open_issue="41")
                self.assertEqual(calls, ["issue comment 41"])

    def test_a_dry_run_reaches_the_lookup_and_writes_nothing(self):
        """The dry-run bail-out from the behavioural side.

        Its sibling in `DispatchAndDryRunTests` proves no write STATEMENT sits
        above the bail-out. This proves the flag is actually consulted: a
        script that built the guard correctly and compared the wrong variable
        would satisfy the shape test and write on every dispatch.
        """
        # On the dispatch, because that is the only event a dry run can happen
        # on: `inputs` is empty everywhere else, so PROBE_DRY_RUN renders as ''
        # on the schedule and the literal "true" can only come from the button.
        calls, out, _, _ = self.run_step(gate="failure", arms_result="success",
                                         open_issue="41", dry_run="true",
                                         event="workflow_dispatch")
        self.assertEqual(calls, [])
        # Detection still ran — the dry run prints what the lookup found, which
        # is the half of this step that has ever been wrong. The event is in
        # that line too, now that it is one of the facts deciding the outcome:
        # a reader of a dry run should not have to know the close is
        # schedule-only to work out that this one would not have closed.
        self.assertIn("open-issue=41", out)
        self.assertIn("gate=failure", out)
        self.assertIn("event=workflow_dispatch", out)


class AccountDriftWorkflowTests(_DryRunStepContract, unittest.TestCase):
    """The contract above, bound to account-store-drift.yml's `react` job.

    This workflow reacts to the Tier-3 audit's PUBLISHED result rather than to
    a run of its own, so two of its properties are load-bearing in ways
    propagation.yml's are not, and both are asserted here.

    It must not listen for a push on the results branch. ROUTINE.md step 4
    mandates a publish message carrying a CI-skip token, so GitHub creates no
    workflow run for those pushes at all: a listener would never fire, and
    would leave no trace of not firing. `PublishMessageAndPushTriggerTests`
    catches that across the whole workflow set; the assertion here is the
    narrow one that this file, whose entire reason to be scheduled is that
    trap, never grows the trigger.

    And its `issues: write` grant covers a six-step job rather than a one-step
    one, because the decision needs a checkout, a Python and a clone of
    `eval-results` before it can be made. The contract's usual "the job is one
    step" guarantee is therefore unavailable, and something has to replace it:
    `test_only_the_write_step_is_handed_a_privileged_environment` does, in the
    three parts `_privilege_findings` applies.

    All three are needed, and the first was shipped alone. It scans for a
    credential handed to a step — but only through `env:`, which is one of the
    three ways an action gets one. `uses: peter-evans/create-issue-from-file`
    takes its token through `with:`, and `uses: actions/github-script` takes
    one through neither: its `github-token` input DEFAULTS to
    `${{ github.token }}`, so a step carrying nothing but a `script:` writes
    the issue under this job's grant with no shell and no visible credential
    at all. Both were inserted into this workflow while the audit read `env:`
    alone and the whole suite stayed green — which is why the second part is
    not another pattern but a closed set: every step here is a `run:` step, or
    one of the two actions this suite has read, or a failure. An action nobody
    examined cannot be argued about from its `env:`.

    The third part is about WHERE a credential is declared rather than which
    step holds it, and it is the one route on which the first two report a
    clean job while every step in it is armed. A step census is handed
    `job["steps"]`, so it can only ever read step-level keys — but `env:` is
    INHERITED, and a `jobs.react.env:` or a workflow-level `env:` carrying
    `GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}` hands one to all six steps in a
    single line. The census then still reports exactly one carrier, because
    the write step goes on declaring its own, and the audit says nothing at
    all. So a credential at either scope is REFUSED rather than counted:
    exactly one step here may write and it declares its own `env:`, which
    leaves a broader declaration nothing to do except widen the blast radius.
    Structural rather than live — no such block exists in this workflow today,
    which is the difference between this part and the two above it: they were
    written after an insertion walked past the audit, this one before.

    Under those three, the structural claim finally holds: a step reaching the
    tracking issue needs a credential, `gh` and `curl` get one only from the
    environment, and every action that could be handed one implicitly is named
    here. A `run:` step spelling `gh issue create` with no token in its `env:`
    is deliberately NOT a finding — `gh` refuses to call the API without one,
    so it reds the run rather than writing, and pinning it would be the
    denylist-of-spellings this suite argues against everywhere else.
    """

    WORKFLOW = REPO_ROOT / ".github" / "workflows" / "account-store-drift.yml"
    JOB = "react"
    WRITE_STEP = "Create, update or close the tracking issue (a dry run prints instead)"
    DECIDE_STEP = "Decide whether the drift issue should exist"
    # Three, not two: this issue is EDITED in place while a drift episode
    # lasts, and CLOSED when the next audit reads pass. A `gh issue comment`
    # here would be the daily-pile failure the reactor exists to avoid.
    WRITE_SPELLINGS = ("gh issue create", "gh issue edit", "gh issue close")
    # Any workflow expression that hands a step a credential EXPLICITLY. Read
    # as a denylist it would be weak; read as this test uses it — "the write
    # step is the ONLY step carrying one" — it is a whitelist of one. It is
    # matched against `env:` AND `with:` values, because an action takes its
    # token through `with:` (`peter-evans/create-issue-from-file`'s `token:`)
    # and never needs an `env:` entry to hold one. And it is matched at three
    # SCOPES, not one: the same expression under `jobs.react.env:` or the
    # workflow's own `env:` arms every step at once, and a census reading
    # step-level keys cannot see either — see the class docstring's third part.
    PRIVILEGED_ENV_RE = re.compile(r"secrets\.|github\.token")
    # And the route no regex over the workflow can see: an action whose token
    # input is DEFAULTED for it. `actions/github-script` defaults
    # `github-token` to `${{ github.token }}`, so a step consisting of nothing
    # but `script:` writes an issue under this job's grant. The only defence
    # against that is knowing which actions run here, so this is a closed set
    # rather than a pattern — an unrecognised `uses:` is a finding.
    #
    # Matched by `owner/name@` so a pin bump stays green while a swap to a
    # different action does not. Neither entry is claimed to be token-free:
    # `actions/checkout`'s own `token` input defaults to `github.token` too,
    # which is exactly what
    # `test_every_checkout_in_the_job_declines_to_persist_a_credential` covers
    # by requiring `persist-credentials: false`. The claim is narrower and
    # checkable — these two are read, and nothing else is.
    EXAMINED_ACTIONS = ("actions/checkout@", "actions/setup-python@")
    # Insertions that really reach the tracking issue, each one placed in this
    # job during review while the audit read `env:` alone — and the whole suite
    # stayed OK on every one of them. `_privilege_findings` has to name each,
    # and the negative control below is what proves it still does; an audit
    # nobody has watched refuse anything is not an audit.
    #
    # A bare `run: gh issue create …` with no `env:` is deliberately absent:
    # it carries no credential, so `gh` refuses the API call and the run goes
    # red instead of writing. That is the structural claim in the docstring,
    # not a gap — see it there for why naming the spelling would be worse.
    #
    # Each route also names WHICH part has to catch it, because the parts do
    # not cover the same ground and "something complained" cannot tell them
    # apart. Both insertions are `uses:` steps, so the closed-set census names
    # both — which means the `with:` scan could be deleted outright and a
    # control that only asked whether the list was non-empty would stay green
    # on the very route the scan was added for. That measurement is of the
    # WEAKER control, taken while it was still the one standing here:
    # reverting the scan to `("env",)` left all 17 tests in this class OK. It
    # is NOT a property of the code as it stands, and reading it as one is the
    # mistake the number invites — re-measured 2026-08-21 against the control
    # below, the same revert reds the `with:` subTest and nothing else, out of
    # 18. Which is the entire reason the complaint match was added. So the
    # parts are pinned one route each, and a revert of any one is a red test
    # rather than a silent loss of coverage.
    CREDENTIAL_COMPLAINT = "steps handed a credential explicitly"
    UNEXAMINED_COMPLAINT = "steps running an action this suite has not read"
    # The third part's complaint, and it names the scope it fired on so the
    # control below can hold the job route and the workflow route apart. They
    # are two entries in one loop, not one check: deleting either entry has to
    # red exactly one route. Two checks that can only be reverted together are
    # one check wearing two names, which is the failure the comment above
    # describes, a level down.
    SCOPE_COMPLAINT = "a credential declared above step scope"
    WRITE_ROUTES_THAT_WALKED_PAST_THE_ENV_SCAN = (
        ("an action handed a token through `with:`",
         {"uses": "peter-evans/create-issue-from-file@" + "0" * 40,
          "with": {"token": "${{ secrets.GITHUB_TOKEN }}",
                   "title": "x", "content-filepath": "body.md"}},
         CREDENTIAL_COMPLAINT),
        ("an action whose token input is defaulted for it",
         {"uses": "actions/github-script@" + "0" * 40,
          "with": {"script": "github.rest.issues.create({...})"}},
         UNEXAMINED_COMPLAINT),
    )

    # The third part's routes: the SCOPE a credential is declared at, spliced
    # into the mapping that owns it rather than into the step list. Neither is
    # a `uses:` step, so the closed-set census cannot reach either, and the
    # step census reads step-level keys only — which the control asserts
    # directly by requiring it to stay SILENT on both. That is what makes this
    # part load-bearing rather than a second opinion: delete it and the audit
    # finds nothing at all on a job whose every step holds a token.
    #
    # (scope, what a reader would see in the diff). The value spliced in is
    # the real spelling — `${{ secrets.GITHUB_TOKEN }}` is what a reviewer
    # adding "just an env var" would reach for, and it is indistinguishable at
    # a glance from the write step's own legitimate line.
    SMUGGLED_CREDENTIAL = {"GH_TOKEN": "${{ secrets.GITHUB_TOKEN }}"}
    SCOPE_ROUTES_THE_STEP_CENSUS_CANNOT_SEE = (
        ("job", "an `env:` on jobs.react, inherited by all six steps"),
        ("workflow", "a workflow-level `env:`, inherited by every job in the "
                     "file — including the one holding `issues: write`"),
    )

    PROLOGUE_ALLOWLIST = (
        ("shell options", r"set -euo pipefail", {}),
        # `if gh api …; then` is deliberately NOT this shape: the pattern is
        # anchored on `[` … `]`, and the budget then allows only the one `;`
        # that `]; then` needs.
        ("a `[` test", r"if \[ .* \]; then", {";": 1}),
        ("a shell keyword", r"else", {}),
        ("a shell keyword", r"fi", {}),
        ("a print", r"echo .*", {}),
        # The body the decider rendered, printed back into the log so a dry run
        # shows what it would have posted. `cat` of a file this job wrote is a
        # read; it reaches nothing.
        ("printing the rendered body", r'cat "\$BODY_FILE"', {}),
        # One `$( )` for the substitution itself, and TWO `|` — the jq filter's
        # own pipe, plus the one inside the marker predicate `(.body // "") |
        # contains(...)`. Spelling the budget out is what rejects
        # `; gh issue create` chained on the end and `| tee >(gh api …)` piped
        # into the middle, both of which fullmatch the pattern otherwise.
        (_DryRunStepContract.DEDUPE_LOOKUP,
         r"number=\$\(gh issue list .*\)", {"$(": 1, "|": 2}),
        ("the bail-out itself", r"exit 0", {}),
    )

    def select_step(self):
        named = [s for s in self.job["steps"]
                 if (s.get("name") or "") == self.WRITE_STEP]
        self.assertEqual(
            len(named), 1,
            f"expected exactly one step named {self.WRITE_STEP!r} in the "
            f"{self.JOB!r} job; found "
            f"{[s.get('name') or s.get('uses') for s in self.job['steps']]}. "
            "This suite lints that step by name, so a rename silently moves "
            "the dry-run guard out from under every assertion below.")
        return named[0]

    def test_the_workflow_declares_no_push_trigger(self):
        self.assertEqual(
            sorted(self.triggers), ["schedule", "workflow_dispatch"],
            "this workflow reads the Routine's PUBLISHED result on a schedule. "
            "A `push:` trigger on the results branch cannot work — the "
            "mandated publish message carries a CI-skip token, so GitHub "
            "creates no run for it — and a `push:` on main would file an "
            "account-drift issue for a code change that cannot cause one.")

    def test_exactly_one_job_holds_the_issue_write_grant(self):
        self.assertEqual(
            self.doc["permissions"], {"contents": "read"},
            "the workflow-level grant stays read-only so a job added later "
            "inherits nothing that can write")
        granted = sorted(name for name, job in self.doc["jobs"].items()
                         if (job.get("permissions") or {}).get("issues") == "write")
        self.assertEqual(
            granted, [self.JOB],
            f"exactly one job may raise `issues: write`; found {granted}")

    def _privilege_findings(self, job, workflow) -> list[str]:
        """Every way `job` breaks "only the write step can reach the issue".

        Takes the JOB and WORKFLOW mappings rather than a list of steps,
        because a credential does not have to be declared on a step to reach
        one. `env:` is inherited, so `jobs.react.env:` and the workflow's own
        `env:` each arm every step in scope — and an audit handed `job["steps"]`
        is looking at the only place such a declaration is NOT. That is the
        third part below, and it reports on mappings the earlier two never see.

        A list of complaints rather than a bare assertion, so the negative
        controls below can drive the SAME audit the real job is measured
        against. A guard reimplemented in its own test proves the copy works.
        """
        findings = []
        # ---- the scopes above the step ----
        # Refused outright rather than counted as carriers, because there is
        # no legitimate reading of one: exactly one step here may write and it
        # declares its own `env:`, so a broader declaration cannot narrow
        # anything and can only hand a token to the five steps that must not
        # have one. Counting instead would also read strangely — a job-level
        # entry is not "a step carrying a credential", it is every step at
        # once, and a complaint listing all six names hides which line did it.
        #
        # `env:` alone at these scopes, deliberately. `with:` and `secrets:`
        # are keys of a REUSABLE-WORKFLOW call (`jobs.<id>.uses:`), and a
        # `react` job written that way carries no `steps:` at all — so
        # `setUp`'s `self.doc["jobs"][self.JOB]["steps"]` raises before any of
        # this runs, which is the loud failure that shape deserves. The
        # `secrets: inherit` route needs a `workflow_call` trigger, and
        # `test_the_workflow_declares_no_push_trigger` pins the trigger list
        # to exactly ["schedule", "workflow_dispatch"] by equality.
        for scope, mapping in (("job", job), ("workflow", workflow)):
            declared = sorted(
                name for name, value in (mapping.get("env") or {}).items()
                if self.PRIVILEGED_ENV_RE.search(str(value)))
            if declared:
                findings.append(
                    f"{self.SCOPE_COMPLAINT} ({scope} scope): {declared} — "
                    "an `env:` here is inherited by every step in scope, so "
                    "this arms the whole job in one line while the step "
                    f"census below still reports [{self.WRITE_STEP!r}]")
        carriers = []
        for step in job["steps"]:
            # `env:` AND `with:`: an action takes its token through `with:`,
            # and reading only `env:` is how the routes named above walked
            # past this audit while the suite stayed green.
            values = " ".join(
                str(value)
                for source in ("env", "with")
                for value in (step.get(source) or {}).values())
            if self.PRIVILEGED_ENV_RE.search(values):
                carriers.append(step.get("name") or step.get("uses"))
        if carriers != [self.WRITE_STEP]:
            findings.append(
                f"{self.CREDENTIAL_COMPLAINT}: {carriers} — expected "
                f"exactly [{self.WRITE_STEP!r}]")
        # The closed set. A `run:` step reaches the API only with a credential,
        # which the scan above accounts for; an ACTION can be handed one
        # invisibly, so an action this suite has not read is a finding on
        # sight rather than something to reason about from its inputs.
        unexamined = [step.get("name") or step.get("uses")
                      for step in job["steps"]
                      if "run" not in step
                      and not str(step.get("uses") or "").startswith(
                          self.EXAMINED_ACTIONS)]
        if unexamined:
            findings.append(
                f"{self.UNEXAMINED_COMPLAINT}: {unexamined}"
                f" — the examined set is {list(self.EXAMINED_ACTIONS)}")
        return findings

    def test_only_the_write_step_is_handed_a_privileged_environment(self):
        """What replaces "the job is exactly one step" — see the class docstring.

        `gh` with no token in its environment refuses to reach the API, so a
        step with no credential cannot write to the tracking issue however it
        is spelled. That makes "one step carries a credential" a structural
        claim rather than a census of command names, which is the same reason
        the prologue guard is an allowlist and not a denylist — but the claim
        only holds once "carries a credential" covers `with:`, once every
        action that could be handed one implicitly has been named, and once
        the two scopes ABOVE the step — the job's `env:` and the workflow's —
        are refused outright. A credential at either of those is handed to
        every step in scope, so it is the one way "only the write step carries
        one" can be false while a census of the steps says it is true.
        """
        self.assertEqual(
            self._privilege_findings(self.job, self.doc), [],
            "every step in this job runs under its `issues: write` grant, and "
            "this audit is the whole of what stops one of them reaching the "
            "tracking issue. A new step belongs in the examined set with a "
            "reason, or it does not belong in this job.")

    def test_the_privilege_audit_refuses_each_route_that_once_walked_past_it(self):
        """The negative control: watch the audit refuse, one route each.

        `test_only_the_write_step_is_handed_a_privileged_environment` passes on
        a clean job — and it also passed on a job carrying either insertion
        below, for as long as it read `env:` alone. A guard measured only
        against input it accepts cannot tell "nothing is wrong" from "nothing
        is being checked", which is the failure this whole suite is built
        around. So each route is spliced into the REAL job here and the audit
        has to name it.

        And each route is checked against the part that has to catch it, not
        merely against the list being non-empty. Those parts overlap on these
        two insertions — both are `uses:` steps, so the closed-set census
        names both — and a control that accepted any complaint would therefore
        stay green with the `with:` scan deleted, on the route that scan
        exists for. Asking WHICH guard fired is what makes them independently
        revertible-and-red.

        Hermetic and deterministic: the splice is a dict appended to a parsed
        document in memory. Nothing is written to the workflow file, so a
        crashed run cannot leave an attack step in the repo.
        """
        for route, step, complaint in self.WRITE_ROUTES_THAT_WALKED_PAST_THE_ENV_SCAN:
            with self.subTest(route=route):
                spliced = dict(self.job, steps=self.job["steps"] + [step])
                findings = self._privilege_findings(spliced, self.doc)
                self.assertTrue(
                    findings,
                    f"{route} was spliced into the {self.JOB!r} job and the "
                    "audit found nothing. It runs under the job's `issues: "
                    "write` grant, needs no shell, and sits entirely outside "
                    "the dry-run bail-out — so even a dry dispatch would "
                    f"write: {step!r}")
                self.assertTrue(
                    [f for f in findings if f.startswith(complaint)],
                    f"{route} was caught, but not by the guard that owns it: "
                    f"expected a {complaint!r} finding and got {findings}. "
                    "Another part happens to cover this route today, so the "
                    "guard named here could be deleted with the suite still "
                    "green — which is the coverage this control exists to "
                    "deny.")

    def test_the_privilege_audit_refuses_a_credential_above_step_scope(self):
        """The third part's control: a token nobody put on a step.

        The two routes above are steps, and a step census can at least SEE
        them. This one it cannot: `jobs.react.env:` and the workflow's own
        `env:` are inherited by every step in scope, so one line arms all six
        while the write step goes on declaring its own — and `carriers` comes
        back as exactly `[WRITE_STEP]`, the value that means everything is
        fine. That is asserted here directly rather than assumed: each subTest
        requires the step census to stay SILENT on its splice. Delete the
        scope refusal and this control does not fall back on another part, it
        finds nothing at all, which is the point of writing it that way.

        The job route and the workflow route are two entries in one loop and
        are pinned one subTest each, for the same reason the control above
        names its guards: two checks that can only be reverted together are
        one check wearing two names.

        Hermetic and deterministic, like the control above: `dict(mapping,
        env=...)` builds a shallow copy of the parsed document and the
        original is never touched, so nothing can leave a credential
        declaration in the workflow file.
        """
        for scope, route in self.SCOPE_ROUTES_THE_STEP_CENSUS_CANNOT_SEE:
            with self.subTest(scope=scope):
                armed = {"job": self.job, "workflow": self.doc}[scope]
                armed = dict(armed, env=dict(self.SMUGGLED_CREDENTIAL))
                job = armed if scope == "job" else self.job
                workflow = armed if scope == "workflow" else self.doc
                findings = self._privilege_findings(job, workflow)
                self.assertTrue(
                    findings,
                    f"{route} was spliced into the parsed workflow and the "
                    f"audit found nothing. Every step in the {self.JOB!r} job "
                    "then holds a credential under its `issues: write` grant "
                    "— including the five that run before the write step, and "
                    "so before the dry-run bail-out exists to withhold "
                    f"anything: {self.SMUGGLED_CREDENTIAL!r}")
                expected = f"{self.SCOPE_COMPLAINT} ({scope} scope)"
                self.assertTrue(
                    [f for f in findings if f.startswith(expected)],
                    f"{route} was caught, but not by the guard that owns it: "
                    f"expected an {expected!r} finding and got {findings}. A "
                    "job-scope and a workflow-scope declaration are separate "
                    "lines in separate mappings, and a control that accepted "
                    "either complaint would stay green with one of them "
                    "unread.")
                self.assertEqual(
                    [f for f in findings
                     if f.startswith(self.CREDENTIAL_COMPLAINT)], [],
                    "the step census was expected to report NOTHING on this "
                    "splice — it reads step-level keys, and this credential "
                    "is not on a step. If it starts complaining, the two "
                    "parts have begun to overlap and the scope refusal could "
                    "be deleted with this control still green: "
                    f"{findings}")

    def test_every_checkout_in_the_job_declines_to_persist_a_credential(self):
        # A checkout that persists its credential leaves one in .git/config for
        # every later step in the job, which would quietly undo the test above.
        checkouts = [s for s in self.job["steps"]
                     if str(s.get("uses") or "").startswith("actions/checkout@")]
        self.assertTrue(checkouts, "expected at least one checkout step")
        for step in checkouts:
            self.assertIs(
                (step.get("with") or {}).get("persist-credentials"), False,
                f"{step.get('name')!r} must set persist-credentials: false")

    def test_the_decision_is_made_before_the_write_step(self):
        # The write step reads `steps.decide.outputs.*`. If the decider ran
        # after it — or stopped being a step at all — those expressions render
        # as empty strings, the policy variable is neither "none" nor a known
        # policy, and the `case` falls through silently: a daily green run that
        # never writes anything.
        names = [s.get("name") or s.get("uses") for s in self.job["steps"]]
        self.assertIn(self.DECIDE_STEP, names)
        self.assertLess(names.index(self.DECIDE_STEP), names.index(self.WRITE_STEP))
        decide = self.job["steps"][names.index(self.DECIDE_STEP)]
        self.assertEqual(decide.get("id"), "decide",
                         "the write step reads steps.decide.outputs.*, so the "
                         "decider's `id:` is part of the wiring")
        for output in ("title", "marker", "policy", "body_file"):
            self.assertIn(
                f"steps.decide.outputs.{output}",
                " ".join(str(v) for v in (self.step.get("env") or {}).values()),
                f"the write step must read {output} from the decider rather "
                "than restating it — two copies of one identifier is one copy "
                "that eventually disagrees")

    # ---- the header's one measurable claim ----
    #
    # The claim, lowercased: a fired session cannot reach the GitHub API. The
    # first draft of this workflow's header gave that as the reason CI owns
    # the issue lifecycle, and called it measured. What was measured was the
    # premises — a fired session carries no `mcp__*` tool, and that
    # environment has no `gh` binary — and the conclusion does not follow from
    # them: `Bash` is in every Routine's allowlist and the agent proxy
    # attaches a credential to outbound HTTPS, so a plain curl with no
    # Authorization header of its own answered 200 for this repository on
    # 2026-08-21. The reasons that survive are about ownership.
    REFUTED_CLAIM = "no route to the github api"

    def _header_paragraphs(self):
        """The leading `#` block, as paragraphs split on blank comment lines."""
        paragraphs, current = [], []
        for raw in self.WORKFLOW.read_text(encoding="utf-8").splitlines():
            if not raw.startswith("#"):
                break
            text = raw.lstrip("#").strip()
            if text:
                current.append(text)
            elif current:
                paragraphs.append(" ".join(current))
                current = []
        if current:
            paragraphs.append(" ".join(current))
        self.assertGreater(
            len(paragraphs), 3,
            "this workflow's header carries the whole argument for its own "
            "existence; a parse that found almost none of it would let the "
            "assertion below pass without reading anything")
        return paragraphs

    def test_the_header_never_repeats_the_refuted_claim_without_its_refutation(self):
        """A false sentence in a header is the one the next person quotes.

        Not a ban on the words — the header is allowed, and expected, to name
        the claim in order to say it was tried and does not hold. What it may
        not do is state it and leave it standing. So any paragraph that says
        the fired session cannot reach the API must carry the measurement that
        refuted it, in the same paragraph, where nobody can quote one without
        the other.
        """
        paragraphs = self._header_paragraphs()
        for paragraph in paragraphs:
            if self.REFUTED_CLAIM not in paragraph.lower():
                continue
            self.assertIn(
                "200", paragraph,
                "the paragraph above states that the fired session has no "
                "route to the GitHub API, and does not say that the claim was "
                "measured false. Its premises hold and its conclusion does "
                "not — `Bash` is in the Routine allowlist and the agent "
                "proxy credentials outbound HTTPS, so an unauthenticated curl "
                "answered 200 for this repository. State it with its "
                "refutation, or not at all.")
        self.assertTrue(
            any("published artifact" in p.lower() or "reviewable" in p.lower()
                for p in paragraphs),
            "the header must still say WHY CI owns this lifecycle. The reasons "
            "that survive measurement are about ownership — the thing that "
            "measures must not also be the thing that reports, and a prompt is "
            "not reviewable, diffable or testable — not about what a fired "
            "session is capable of.")

    # ---- the policy the decider emits, and what the `case` does with it ----
    #
    # Everything below reads the WIRING out of the workflow rather than
    # restating it: which variable the `case` switches on, which step output
    # feeds that variable, and which flags the decide step passes. That is not
    # ceremony. The defect these were written for was invisible to every test
    # that named the pieces itself — `decide` had a `close` branch and the
    # `case` had a `close)` arm, both correct in isolation, and the workflow
    # invoked the decider in the one way that could never produce `close`.
    # Only something that follows the wire from one end to the other sees it.

    CASE_RE = re.compile(r'^\s*case\s+"\$(\w+)"\s+in\s*$')
    ARM_RE = re.compile(r"^([^()#;]+)\)$")

    def _case_arms(self):
        """(variable the `case` switches on, {arm pattern: [command lines]}).

        COMMENTS ARE DROPPED from every arm body, which is the point of
        parsing at all: an arm whose only mention of `gh issue close` is in a
        comment explaining what it would do closes nothing, and "the word
        appears in the step" is the check that let a dead close path ship.
        """
        lines = self.step["run"].splitlines()
        variable, arms, arm = None, {}, None
        for raw in lines:
            line = raw.strip()
            if variable is None:
                found = self.CASE_RE.match(raw)
                if found:
                    variable = found.group(1)
                continue
            if line == "esac":
                break
            if not line or line.startswith("#"):
                continue
            if arm is None:
                found = self.ARM_RE.match(line)
                self.assertIsNotNone(
                    found, f"unparsed line between `case` arms: {line!r}. This "
                    "parse is what every assertion below stands on, so it "
                    "fails rather than skipping what it did not understand.")
                arm = found.group(1).strip()
                self.assertNotIn(arm, arms, f"two `{arm})` arms; the second is dead")
                arms[arm] = []
                continue
            if line == ";;":
                arm = None
                continue
            arms[arm].append(line)
        self.assertIsNotNone(
            variable, "the write step must map the policy onto a `gh` call in "
            'a `case "$VAR" in` — nothing else here is parseable, and an '
            "unparseable step is one this suite cannot check at all")
        self.assertIsNone(arm, f"the `{arm})` arm is never closed with `;;`")
        self.assertTrue(arms, "a `case` with no arms handles no policy")
        return variable, arms

    def _bail_out_value(self):
        """The one policy the step handles by exiting instead of by an arm."""
        variable, _ = self._case_arms()
        pattern = re.compile(r'if \[ "\$%s" = "(\w+)" \]; then' % variable)
        found = [pattern.search(line) for line in self.step["run"].splitlines()]
        hits = [m.group(1) for m in found if m]
        self.assertEqual(
            len(hits), 1,
            f"expected exactly one `${variable}` bail-out test; found {hits}")
        return hits[0]

    def _policy_output_name(self):
        """Which decider output feeds the variable the `case` switches on."""
        variable, _ = self._case_arms()
        expression = str((self.step.get("env") or {}).get(variable, ""))
        found = re.search(r"steps\.decide\.outputs\.(\w+)", expression)
        self.assertIsNotNone(
            found,
            f"the `case` switches on ${variable}, which the step's env must "
            f"take from a decider output; it is {expression!r}")
        return found.group(1)

    def _run_the_decider_as_the_workflow_does(self, summary):
        """The decider's step outputs, invoked with the workflow's own flags.

        The argv is READ OUT of the decide step — only the three paths and a
        fixed `--now` are substituted, every flag is copied verbatim — so a
        flag that changes what the decider can conclude is exercised here
        rather than described. `--existing-issue-number ""` was such a flag:
        harmless-looking, impossible for any caller to fill in, and it
        collapsed the `fresh` verdict to "do nothing" on every run.
        """
        root = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, root, ignore_errors=True)
        latest = root / "propagation" / "account" / "latest.json"
        latest.parent.mkdir(parents=True)
        latest.write_text(json.dumps(summary), encoding="utf-8")
        marker = root / "propagation" / ".bootstrapped"
        marker.touch()
        body, outputs = root / "body.md", root / "step-outputs.txt"

        names = [s.get("name") or s.get("uses") for s in self.job["steps"]]
        decide = self.job["steps"][names.index(self.DECIDE_STEP)]
        script = re.sub(r"\\\n\s*", " ", decide["run"])
        calls = [line.strip() for line in script.splitlines()
                 if "run_account_drift_issue.py" in line
                 and not line.strip().startswith("#")]
        self.assertEqual(len(calls), 1,
                         f"expected one decider invocation; found {calls}")
        tokens = shlex.split(calls[0])
        self.assertTrue(
            tokens[1].endswith("run_account_drift_issue.py"),
            f"expected `python3 harness/run_account_drift_issue.py …`; got {tokens[:2]}")
        substitutions = {"--account-latest": str(latest),
                         "--account-marker": str(marker),
                         "--body-out": str(body)}
        argv, rest, positionals = [], tokens[2:], 0
        while rest:
            token, rest = rest[0], rest[1:]
            if token in substitutions:
                argv += [token, substitutions[token]]
                rest = rest[1:]
            elif token.startswith("--"):
                argv.append(token)
                if rest and not rest[0].startswith("--"):
                    argv.append(rest[0])
                    rest = rest[1:]
            else:
                positionals += 1
                argv.append(str(EVAL_DIR))
        self.assertEqual(positionals, 1,
                         "the decider takes exactly one positional, the eval dir")
        # `--now` is the suite's, not the workflow's: this file runs on no
        # clock. Everything else above came out of the workflow.
        argv += ["--now", NOW.strftime("%Y-%m-%dT%H:%M:%SZ")]

        with mock.patch.dict(os.environ, {"GITHUB_OUTPUT": str(outputs)}), \
                contextlib.redirect_stdout(io.StringIO()):
            code = run_account_drift_issue.main(argv)
        self.assertEqual(code, 0, "a verdict is a finding, never an exit code")
        return dict(line.split("=", 1) for line
                    in outputs.read_text(encoding="utf-8").splitlines() if line)

    def _published(self, status):
        return {"schema": 1, "probe": "propagation/account", "status": status,
                "generated_at": datetime.fromtimestamp(
                    NOW.timestamp() - 0.5 * 86400,
                    timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "registry_ref": "0" * 40, "checked": ["fixture-alpha"],
                "skipped": [], "findings": []}

    def test_the_close_policy_reaches_gh_issue_close(self):
        """A repaired store must arrive at `gh issue close`, through the wire.

        THE REGRESSION TEST FOR A LIFECYCLE WITH NO CLOSE IN IT. `decide` used
        to be handed the open issue's number and return `close` only when one
        was supplied. Nothing upstream of the credentialed step can supply
        one, so the workflow passed `--existing-issue-number ""` on every run;
        a `fresh` verdict therefore returned `none`, and the write step's
        first line exits on `none`. The issue opened on the first red and
        would have stayed open through every green day afterwards, below a
        body that promises "the next audit that reads `pass` closes it".

        Everything the decider is told here comes out of the decide step, and
        the arm is found by parsing the `case` — because both halves were
        individually correct while the whole was dead, and only running one
        into the other shows it.
        """
        outputs = self._run_the_decider_as_the_workflow_does(
            self._published("pass"))
        output_name = self._policy_output_name()
        self.assertIn(
            output_name, outputs,
            f"the write step reads `steps.decide.outputs.{output_name}`, which "
            f"the decider never writes; it writes {sorted(outputs)}")
        policy = outputs[output_name]

        _, arms = self._case_arms()
        closing = [pattern for pattern, commands in arms.items()
                   if policy in [alt.strip() for alt in pattern.split("|")]
                   and any("gh issue close" in command for command in commands)]
        self.assertEqual(
            len(closing), 1,
            f"a store that reads `pass` produced policy {policy!r} from the "
            "decide step's own invocation, and no `case` arm matching "
            f"{policy!r} runs `gh issue close` — arms: {sorted(arms)}, "
            f"bail-out: {self._bail_out_value()!r}. Nothing closes the "
            "tracking issue, so it outlives the drift it reports while its "
            "body promises the next passing audit will close it.")

    def test_every_policy_the_decider_emits_is_handled_by_the_write_step(self):
        """No policy without an arm, and no arm without a policy.

        Both directions, because both are silent. A policy with no arm falls
        through the `case` and the run goes green having written nothing; an
        arm no policy can produce is dead shell that reads as coverage.
        """
        variable, arms = self._case_arms()
        alternatives = {alt.strip() for pattern in arms
                        for alt in pattern.split("|")}
        emitted = {run_account_drift_issue.decide(status) for status, _, _
                   in AccountDriftIssueDecisionTests.TABLE}
        self.assertTrue(emitted, "the status table produced no policy at all")
        bail_out = self._bail_out_value()
        self.assertIn(
            bail_out, emitted,
            f"the step exits early on ${variable} == {bail_out!r}, which the "
            "decider never emits — so the early exit is unreachable and every "
            "policy falls through to the `case`")
        self.assertEqual(
            emitted - {bail_out}, alternatives,
            f"the decider emits {sorted(emitted)} and the `case` handles "
            f"{sorted(alternatives)} beside the {bail_out!r} bail-out. A "
            "policy with no arm is a green run that writes nothing; an arm no "
            "policy reaches is dead shell that looks like coverage.")

    # ---- the dedupe lookup's jq filter, RUN rather than read ----

    def _dedupe_jq_filter(self):
        script = re.sub(r"\\\n\s*", " ", self.step["run"])
        lookups = [line.strip() for line in script.splitlines()
                   if "gh issue list" in line and not line.strip().startswith("#")]
        self.assertEqual(len(lookups), 1,
                         f"expected one dedupe lookup; found {lookups}")
        # Single-quoted by shell convention and containing no `'` of its own,
        # so this is exact rather than approximate.
        found = re.findall(r"--jq\s+'([^']*)'", lookups[0])
        self.assertEqual(
            len(found), 1,
            "the dedupe lookup must pass exactly one single-quoted `--jq` "
            f"program, which is what the tests below execute; found {found}")
        return found[0]

    def _dedupe_match(self, issues):
        """What the workflow's own jq filter returns for `issues`.

        RUN, not matched as text. The filter shipped with `and` where it needed
        `or` — a perfectly well-formed program that finds only issues this
        workflow has already written — and every string assertion anyone would
        write about it passes on both versions. `jq` is on the runner and in
        the dev container, so its absence is a failure rather than a skip:
        skipping would leave the one assertion that has ever caught anything
        here unperformed, which is how the `and` shipped.
        """
        jq = shutil.which("jq")
        self.assertIsNotNone(
            jq, "`jq` is required to execute the workflow's dedupe filter; a "
                "text comparison passes on a filter that finds the wrong "
                "issues, which is the defect these tests exist for")
        proc = subprocess.run(
            [jq, "-r", self._dedupe_jq_filter()],
            input=json.dumps(issues), text=True, capture_output=True,
            # The identifiers the workflow puts in this environment are the
            # decider's constants, so the fixture is matched against the same
            # two strings production matches against.
            env={"PATH": os.environ.get("PATH", ""),
                 "ISSUE_TITLE": run_account_drift_issue.TITLE,
                 "ISSUE_MARKER": run_account_drift_issue.MARKER})
        self.assertEqual(proc.returncode, 0,
                         f"the dedupe filter is not valid jq: {proc.stderr.strip()}")
        return proc.stdout.strip()

    def test_the_dedupe_filter_adopts_an_issue_filed_before_the_marker_existed(self):
        """The regression test for a filter that would file a duplicate.

        The tracking issue open on this repo right now was filed by hand
        before the marker was invented: its title is byte-equal to the
        decider's and its body carries no marker at all. Requiring BOTH — the
        filter as first written — finds nothing in that shape, so the very
        first real run takes the create branch and files a SECOND issue for
        the same drift, which is precisely the pile the marker exists to
        prevent. Either half alone must be enough to adopt it.
        """
        self.assertEqual(
            self._dedupe_match([{"title": run_account_drift_issue.TITLE,
                                 "body": "filed by hand, no marker in here",
                                 "number": 48}]),
            "48",
            "an open issue whose title matches exactly must be adopted even "
            "with no marker in its body — the first edit rewrites that body "
            "and the issue acquires the marker, which is how the two halves "
            "converge")

    def test_the_dedupe_filter_still_matches_a_marker_under_a_reworded_title(self):
        # The other half, and the reason the marker exists: a title someone
        # edits by hand stops matching, and the marker is what survives it.
        self.assertEqual(
            self._dedupe_match([{
                "title": "Account store drift — needs a ZIP upload (reworded)",
                "body": f"{run_account_drift_issue.MARKER}\n\nsome body",
                "number": 61}]),
            "61")

    def test_the_dedupe_filter_matches_neither_an_unrelated_issue_nor_nothing(self):
        """The vacuity control for both tests above.

        A filter that returned every issue would pass them and adopt whatever
        the title search happened to return first — `--search` is full text,
        so near-misses do come back. And a filter that returned nothing at all
        would look like "no issue is open", which the step reads as "file a
        new one".
        """
        self.assertEqual(
            self._dedupe_match([{"title": "Account skill store: add a probe",
                                 "body": "unrelated request", "number": 7}]),
            "",
            "a near-miss the title search returned must not be adopted; the "
            "step would then edit somebody else's issue every morning")
        self.assertEqual(self._dedupe_match([]), "",
                         "no open issue must read as empty, not as an error")
        # A body key absent or null is the shape gh returns for an empty body;
        # `.body // ""` is what keeps that from erroring the whole lookup out.
        self.assertEqual(
            self._dedupe_match([{"title": run_account_drift_issue.TITLE,
                                 "body": None, "number": 12}]),
            "12")


class PublishMessageAndPushTriggerTests(unittest.TestCase):
    """ROUTINE.md's publish message and the workflow set must not contradict.

    Step 4 of the Routine prompt mandates the commit message
    `propagation: account audit [skip ci]`, and `[skip ci]` is GitHub's
    documented instruction NOT to create a workflow run for a `push` event. So
    a workflow that tries to react to the Routine's publish with

        on:
          push:
            branches: [eval-results]

    cannot fire on a single one of those pushes. It is not red, not slow, and
    not logged anywhere — it simply never runs, which is the worst shape a CI
    dependency can take. That trap is exactly what a design note in ROUTINE.md
    ("A second route the issue does not consider") records, and prose is not an
    assertion: this pins the pair so the two halves cannot be edited apart.

    The coupling is DERIVED at both ends rather than hard-coded. The message is
    read out of ROUTINE.md's own step 4 (so rewording it is followed, not
    broken) and the listeners are read by parsing every workflow with a real
    YAML parser (never a line scan — a bare `on:` is the YAML 1.1 boolean True,
    which a regex reads straight past). What is asserted is the implication:
    if any workflow listens for a push on `eval-results`, the mandated message
    may not carry a CI-skip token. Removing the token is a legitimate decision
    — it is what stops a results-branch publish feeding CI back into itself, so
    it has consequences of its own — and this test does not forbid it; it
    forbids having it both ways silently.

    `test_the_detector_sees_a_listener_when_there_is_one` is the reason the
    implication is not vacuous today. No workflow here listens on
    `eval-results`, so the guard would pass against a detector that finds
    nothing ever; the positive control runs the same function over a synthetic
    document that does listen, and requires it to be found.
    """

    ROUTINE = EVAL_DIR / "ROUTINE.md"
    WORKFLOWS = REPO_ROOT / ".github" / "workflows"
    RESULTS_BRANCH = "eval-results"
    # GitHub's documented commit-message skip tokens. `skip-checks: true` is a
    # trailer rather than a message token and is deliberately not modelled.
    SKIP_TOKENS = ("[skip ci]", "[ci skip]", "[no ci]", "[skip actions]",
                   "[actions skip]")
    # Lexical on purpose, and legitimately so: this extracts the CONTENT of one
    # leaf token — the inline-code span on the "Commit message:" line — not the
    # structure of anything. The structural half of this test (which events a
    # workflow declares) goes through yaml.safe_load below.
    MESSAGE_RE = re.compile(r"Commit message:\s*`([^`]+)`")

    def _mandated_message(self) -> str:
        found = self.MESSAGE_RE.findall(
            self.ROUTINE.read_text(encoding="utf-8"))
        self.assertEqual(
            len(found), 1,
            "ROUTINE.md must declare the publish commit message exactly once, "
            "as an inline-code span on a `Commit message:` line — that "
            "declaration is what this guard reads. Found: "
            f"{found!r}")
        return found[0]

    @classmethod
    def _listens_on(cls, doc: dict, branch: str) -> bool:
        """Does this parsed workflow raise a run on a push to `branch`?

        Errs toward YES on anything it cannot resolve exactly: an unmatched
        pattern here reds this test and sends someone to look, whereas a missed
        one is the silent never-fires failure the whole guard exists to catch.
        """
        # A bare `on:` key parses as the YAML 1.1 boolean True, not "on".
        triggers = doc.get("on", doc.get(True)) if isinstance(doc, dict) else None
        # `on: push` and `on: [push]` are the two shorthand spellings, and both
        # mean EVERY push on EVERY branch — `eval-results` included. Neither
        # parses to a mapping (`{True: 'push'}` and `{True: ['push']}`
        # respectively), so a mapping-only reader returns False on the exact
        # shapes this guard exists to catch, which is the silent never-fires
        # failure one level up.
        if isinstance(triggers, str):
            return triggers == "push"
        if isinstance(triggers, list):
            return any(str(event) == "push" for event in triggers)
        if not isinstance(triggers, dict):
            # No `on:` at all, or a shape this cannot read. Unresolvable, so
            # say yes and send someone to look — per the docstring above.
            return True
        if "push" not in triggers:
            return False
        push = triggers["push"]
        if not isinstance(push, dict):
            return True  # bare `push:` — every branch, this one included
        if "branches" in push:
            return any(fnmatch.fnmatch(branch, str(pattern))
                       for pattern in push["branches"] or [])
        if "branches-ignore" in push:
            return not any(fnmatch.fnmatch(branch, str(pattern))
                           for pattern in push["branches-ignore"] or [])
        return True  # `push:` with only `paths:` — still every branch

    def _listeners(self) -> list[str]:
        import yaml
        # GitHub Actions reads BOTH extensions, so a `.yaml` workflow is a real
        # workflow that a `*.yml`-only glob never opens.
        paths = sorted(set(self.WORKFLOWS.glob("*.yml"))
                       | set(self.WORKFLOWS.glob("*.yaml")))
        self.assertTrue(
            paths,
            f"no workflows parsed out of {self.WORKFLOWS} — this guard would "
            "pass by finding nothing, which is not the same as agreeing")
        return [path.name for path in paths
                if self._listens_on(
                    yaml.safe_load(path.read_text(encoding="utf-8")),
                    self.RESULTS_BRANCH)]

    def test_the_detector_sees_a_listener_when_there_is_one(self):
        import yaml
        positive = yaml.safe_load(
            "on:\n  push:\n    branches: [eval-results]\n")
        self.assertTrue(
            self._listens_on(positive, self.RESULTS_BRANCH),
            "the listener detector must find the shape the design note warns "
            "about, or the guard below passes for the wrong reason")
        negative = yaml.safe_load("on:\n  push:\n    branches: [main]\n")
        self.assertFalse(
            self._listens_on(negative, self.RESULTS_BRANCH),
            "a push pinned to main is not a listener on the results branch")

    def test_the_detector_sees_the_bare_list_shorthand(self):
        """`on: [push]` means every push on every branch, this one included."""
        import yaml
        positive = yaml.safe_load("on: [push]\n")
        self.assertEqual(
            positive, {True: ["push"]},
            "this spelling parses to a LIST under the boolean-True key, not a "
            "mapping — that is why a mapping-only reader misses it")
        self.assertTrue(
            self._listens_on(positive, self.RESULTS_BRANCH),
            "`on: [push]` is an unfiltered push trigger, so it fires on "
            f"{self.RESULTS_BRANCH!r} like every other branch; a reader that "
            "returns False here would let the `[skip ci]` trap through in the "
            "one shape nothing else catches")
        # Negative control: same shorthand, no push event. Without this a
        # detector hard-wired to `return True` would satisfy the assertion
        # above and detect nothing at all.
        negative = yaml.safe_load("on: [pull_request, workflow_dispatch]\n")
        self.assertEqual(negative, {True: ["pull_request", "workflow_dispatch"]})
        self.assertFalse(
            self._listens_on(negative, self.RESULTS_BRANCH),
            "the list shorthand without `push` is not a push listener — this "
            "control is what proves the case above discriminates")

    def test_the_detector_sees_the_bare_scalar_shorthand(self):
        """`on: push` is the same trap one step smaller."""
        import yaml
        positive = yaml.safe_load("on: push\n")
        self.assertEqual(
            positive, {True: "push"},
            "this spelling parses to a STRING under the boolean-True key")
        self.assertTrue(
            self._listens_on(positive, self.RESULTS_BRANCH),
            "`on: push` is an unfiltered push trigger and fires on "
            f"{self.RESULTS_BRANCH!r}")
        negative = yaml.safe_load("on: workflow_dispatch\n")
        self.assertEqual(negative, {True: "workflow_dispatch"})
        self.assertFalse(
            self._listens_on(negative, self.RESULTS_BRANCH),
            "a scalar naming some other event is not a push listener — the "
            "control that keeps the case above from passing vacuously")

    def test_an_unreadable_trigger_block_errs_toward_yes(self):
        """The docstring's promise, asserted rather than described.

        A shape this cannot resolve must red the guard and send someone to
        look. The alternative — quietly answering "not a listener" — is the
        same silent miss as the two shorthands above.
        """
        self.assertTrue(
            self._listens_on({"jobs": {}}, self.RESULTS_BRANCH),
            "a document with no `on:` key at all is unresolvable, not a "
            "resolved no")
        self.assertTrue(
            self._listens_on(None, self.RESULTS_BRANCH),
            "an empty workflow file parses to None; that is unresolvable too")
        # Negative control: a trigger block this CAN resolve must still resolve
        # to no, or "errs toward yes" has degenerated into "always yes".
        self.assertFalse(
            self._listens_on({True: {"schedule": [{"cron": "0 5 * * *"}]}},
                             self.RESULTS_BRANCH),
            "a readable mapping with no `push` key is a resolved no, and must "
            "not be swept up by the unresolvable fallback")

    def test_a_dot_yaml_workflow_is_read_too(self):
        """`.yaml` is a workflow extension GitHub honours; the glob must too.

        A listener written `.yaml` evaded the guard entirely — not by parsing
        wrong but by never being opened, which leaves no trace at all.
        """
        with tempfile.TemporaryDirectory() as tmp:
            workflows = Path(tmp)
            (workflows / "listener.yaml").write_text(
                "on:\n  push:\n    branches: [eval-results]\njobs: {}\n",
                encoding="utf-8")
            with mock.patch.object(type(self), "WORKFLOWS", workflows):
                self.assertEqual(
                    self._listeners(), ["listener.yaml"],
                    "a `.yaml` workflow that listens on the results branch "
                    "must be found; a `*.yml`-only glob reports an empty list "
                    "and the guard passes for the wrong reason")
            # Negative control: same extension, pinned to main. Proves the case
            # above found a LISTENER rather than merely finding a file.
            (workflows / "listener.yaml").write_text(
                "on:\n  push:\n    branches: [main]\njobs: {}\n",
                encoding="utf-8")
            with mock.patch.object(type(self), "WORKFLOWS", workflows):
                self.assertEqual(
                    self._listeners(), [],
                    "a `.yaml` workflow pinned to main is not a listener on "
                    f"{self.RESULTS_BRANCH!r}")

    def test_no_push_listener_while_the_publish_message_skips_ci(self):
        message = self._mandated_message()
        tokens = [token for token in self.SKIP_TOKENS
                  if token in message.lower()]
        listeners = self._listeners()
        self.assertFalse(
            tokens and listeners,
            f"{listeners} listen for a push on {self.RESULTS_BRANCH!r}, but "
            f"ROUTINE.md step 4 mandates the commit message {message!r}, which "
            f"carries {tokens} — GitHub will not create a workflow run for "
            "such a push, so those workflows never fire on a Routine publish "
            "and say nothing about it. Either drop the token from step 4 and "
            "the live Routine prompt together (it is what keeps a "
            "results-branch publish from feeding CI back into itself, so read "
            "the design note in ROUTINE.md first), or trigger on something "
            "`[skip ci]` does not gate.")


class AccountDriftIssueDecisionTests(unittest.TestCase):
    """The reactor: published verdict -> one tracking issue, and its body.

    `harness/run_account_drift_issue.py` is the half of account-store-drift.yml
    that decides anything, and it is deliberately credential-free so it can be
    driven from here rather than from a live run. Every case below writes a
    `latest.json` by hand, passes a fixed `--now`, and asserts the exact action
    — no clock, no network, no GitHub.

    The two things worth stating about WHY these are the cases:

    * The status table is checked in FULL, including the four liveness statuses
      that must do nothing. Those are the ones a later edit will want to make
      helpful: closing the issue on `stale` looks like tidying up and is really
      retracting a live finding on the strength of no measurement, and opening
      one on `missing` files an account-drift report for what is a broken
      Routine binding. Each case therefore asserts the STATUS it produced as
      well as the action, so a fixture that quietly stopped producing `stale`
      cannot leave the row passing against something else.
    * The body is checked for what it must NOT contain. Both repos are public
      and so is every issue on them; the finding details are free text built by
      interpolating real directories, and on the surface that publishes this
      result those directories sit under `$HOME`.
    """

    def setUp(self):
        self.root = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.root, ignore_errors=True)
        self.latest = self.root / "propagation" / "account" / "latest.json"
        self.latest.parent.mkdir(parents=True)
        self.marker = self.root / "propagation" / ".bootstrapped"
        self.body = self.root / "body.md"
        self.outputs = self.root / "step-outputs.txt"

    def publish(self, *, status="pass", days_ago=0.5, generated=None,
                findings=(), checked=("fixture-alpha",), skipped=()):
        """Write a result in the exact shape the Routine publishes."""
        if generated is None:
            generated = datetime.fromtimestamp(
                NOW.timestamp() - days_ago * 86400,
                timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        self.latest.write_text(json.dumps({
            "schema": 1, "probe": "propagation/account", "status": status,
            "generated_at": generated, "registry_ref": "0" * 40,
            "checked": list(checked), "skipped": list(skipped),
            "findings": [dict(f) for f in findings]}), encoding="utf-8")

    def react(self, *, marker=True, eval_dir=None):
        """(outputs, body, status line) for one run of the decider.

        No issue number goes in, because the decider takes none — see
        `test_the_decider_refuses_to_be_told_an_issue_number`.
        """
        if self.outputs.exists():
            self.outputs.unlink()
        if marker:
            self.marker.touch()
        argv = [str(eval_dir or EVAL_DIR),
                "--account-latest", str(self.latest),
                "--account-marker", str(self.marker),
                "--body-out", str(self.body),
                "--now", NOW.strftime("%Y-%m-%dT%H:%M:%SZ")]
        printed = io.StringIO()
        with mock.patch.dict(os.environ, {"GITHUB_OUTPUT": str(self.outputs)}), \
                contextlib.redirect_stdout(printed):
            code = run_account_drift_issue.main(argv)
        self.assertEqual(code, 0, "a verdict is a finding, never an exit code")
        outputs = dict(line.split("=", 1) for line
                       in self.outputs.read_text(encoding="utf-8").splitlines()
                       if line)
        return outputs, self.body.read_text(encoding="utf-8"), printed.getvalue()

    # (freshness status, how to produce it, the POLICY it must produce). Every
    # status `freshness_verdict` can return, and the policy vocabulary is the
    # whole of it: `open`, `close`, `none`. There is no second column any more
    # — the old table had one action for "an issue is open" and another for
    # "none is", which is a fact this side of the split cannot have and the
    # reason `close` was unreachable in production. What satisfies each policy
    # is the workflow's business, asserted in `AccountDriftWorkflowTests`.
    TABLE = (
        ("not-yet-bootstrapped", dict(marker=False), "none"),
        ("missing", dict(), "none"),
        ("unreadable", dict(publish=dict(generated="the other day")), "none"),
        ("stale", dict(publish=dict(status="fail", days_ago=11)), "none"),
        # The row the whole carve-out is for: a PASS nobody has seen for eleven
        # days is not evidence the drift is over, so it must not close.
        ("stale", dict(publish=dict(status="pass", days_ago=11)), "none"),
        ("reported-failure", dict(publish=dict(status="fail")), "open"),
        ("fresh", dict(publish=dict(status="pass")), "close"),
    )

    def test_every_freshness_status_maps_to_the_documented_policy(self):
        for status, setup, expected in self.TABLE:
            with self.subTest(status=status):
                self.latest.unlink(missing_ok=True)
                if "publish" in setup:
                    self.publish(**setup["publish"])
                self.marker.unlink(missing_ok=True)
                outputs, _, line = self.react(marker=setup.get("marker", True))
                self.assertIn(
                    f"[{status}]", line,
                    f"this row means to exercise {status!r}; the fixture "
                    f"produced {line.strip()!r} instead, so the policy "
                    "below would be asserted against the wrong branch")
                self.assertEqual(outputs["policy"], expected)

    def test_a_repaired_store_asks_for_the_issue_to_be_closed(self):
        """The regression test for a close path nothing could ever reach.

        `decide` used to take the open issue's number and return
        `close` only when one was passed. No caller could pass one — the
        lookup needs a credential and lives a step later — so the workflow
        passed the empty string on every run, `fresh` returned `none`, and the
        write step exited at its first line every green day. The issue that
        opened on the first red would have stayed open forever, under a body
        promising that the next passing audit closes it.

        So: a fresh `pass`, nothing else supplied, must ask for a close. The
        companion assertion — that the policy this returns actually reaches
        `gh issue close` in the workflow — is
        `AccountDriftWorkflowTests.test_the_close_policy_reaches_gh_issue_close`,
        because a policy no arm handles is the same silence in a new place.
        """
        self.publish(status="pass")
        outputs, body, line = self.react()
        self.assertIn("[fresh]", line)
        self.assertEqual(
            outputs["policy"], "close",
            "a repaired store must ask for the tracking issue to be closed "
            "whether or not one is open — whether one is open is not knowable "
            "here, and pretending it was is what stranded this branch")
        self.assertIn("closed automatically", body,
                      "the closing comment is what the reader sees; a `close` "
                      "that renders the drift body would close the issue with "
                      "the text saying it is still broken")

    def test_the_decider_refuses_to_be_told_an_issue_number(self):
        """The flag whose only possible value was the empty string.

        Pinned as a rejection rather than left to review. Reintroducing it is
        the natural "improvement" — it looks like it moves create-vs-update
        into tested code — and it is what silently removed the close branch
        last time, because the number it asks for cannot exist before the
        credentialed step that looks it up.
        """
        self.publish(status="pass")
        with contextlib.redirect_stderr(io.StringIO()), \
                self.assertRaises(SystemExit) as caught:
            run_account_drift_issue.main(
                [str(EVAL_DIR), "--account-latest", str(self.latest),
                 "--existing-issue-number", "48",
                 "--body-out", str(self.body), "--now", "2026-08-14T12:00:00Z"])
        self.assertEqual(caught.exception.code, 2)

    def test_the_liveness_statuses_are_left_to_the_freshness_gate(self):
        """A restatement of four table rows, as the place the reason lives.

        `stale`, `missing`, `unreadable` and `not-yet-bootstrapped` all say the
        audit is not reaching us and say nothing about the account store.
        `propagation.yml`'s freshness gate fails on exactly those, on every
        pull request and on its own schedule. Two mechanisms answering one
        fault in two vocabularies is how they end up contradicting each other.
        """
        for status in ("stale", "missing", "unreadable", "not-yet-bootstrapped"):
            with self.subTest(status=status):
                self.assertEqual(run_account_drift_issue.decide(status), "none")

    def test_a_drifted_store_asks_for_the_issue_to_be_open(self):
        # The edit-in-place rule lives in the workflow's `open` arm, because
        # only that step knows whether an issue is already there. What this
        # side owes it is the policy: a red audit means an issue should exist
        # and say so. A drift episode ran four days the last time one happened
        # (ROUTINE.md); the arm edits rather than comments so a steady-state
        # red does not become a notification stream people filter.
        self.publish(status="fail",
                     findings=[{"skill": "fixture-alpha", "kind": "content-drift",
                                "detail": "SKILL.md differs"}])
        outputs, body, _ = self.react()
        self.assertEqual(outputs["policy"], "open")
        self.assertIn("has drifted from the registry", body)
        self.assertIn("The next audit that reads `pass` closes it", body,
                      "the body promises self-closure; that promise is only "
                      "true while `fresh` maps to `close` and the workflow's "
                      "`close` arm reaches `gh issue close`")

    def test_a_missing_fixture_is_a_usage_error_and_not_a_verdict(self):
        self.publish(status="fail")
        printed = io.StringIO()
        with contextlib.redirect_stdout(printed):
            code = run_account_drift_issue.main(
                [str(self.root / "nowhere"), "--account-latest", str(self.latest),
                 "--body-out", str(self.body), "--now", "2026-08-14T12:00:00Z"])
        self.assertEqual(code, 2)
        self.assertIn("INCONCLUSIVE", printed.getvalue())

    def test_the_step_outputs_carry_what_the_workflow_reads(self):
        self.publish(status="fail")
        outputs, body, _ = self.react()
        self.assertEqual(sorted(outputs),
                         ["body_file", "marker", "policy", "title"])
        self.assertEqual(outputs["title"], run_account_drift_issue.TITLE)
        self.assertEqual(outputs["marker"], run_account_drift_issue.MARKER)
        self.assertEqual(outputs["body_file"], str(self.body))
        self.assertIn(outputs["marker"], body)

    def test_the_marker_is_the_one_routine_md_mandates(self):
        # ROUTINE.md step 5 fixes this string, and the workflow's dedupe lookup
        # matches on it. CI took the lifecycle over from the fired session; if
        # the two identifiers ever diverge, the lookup stops recognising the
        # issue it wrote yesterday and quietly files a second one.
        self.assertIn(run_account_drift_issue.MARKER,
                      (EVAL_DIR / "ROUTINE.md").read_text(encoding="utf-8"))

    def test_every_body_starts_with_the_marker(self):
        for status, setup, policy in self.TABLE:
            with self.subTest(status=status, policy=policy):
                self.latest.unlink(missing_ok=True)
                if "publish" in setup:
                    self.publish(**setup["publish"])
                self.marker.unlink(missing_ok=True)
                _, body, _ = self.react(marker=setup.get("marker", True))
                self.assertTrue(
                    body.startswith(run_account_drift_issue.MARKER),
                    f"{status}/{policy} rendered a body that does not open "
                    "with the marker, so the workflow's lookup would never "
                    "match it again")

    def test_the_body_names_every_drifted_skill(self):
        self.publish(status="fail", checked=("a", "b", "c"), skipped=("d",),
                     findings=[
                         {"skill": "a", "kind": "content-drift", "detail": "x"},
                         {"skill": "a", "kind": "description-drift", "detail": "y"},
                         {"skill": "c", "kind": "no-skill-md", "detail": "z"}])
        _, body, line = self.react()
        for skill in ("a", "c"):
            self.assertIn(f"`{skill}`", body)
        self.assertIn("| drifted | 2 |", body,
                      "two SKILLS drifted across three findings; counting "
                      "findings would overstate the episode every time one "
                      "skill trips two assertions")
        # And the status line stays counts-only: the log is public and the
        # artifact already names the skills.
        self.assertNotIn("`a`", line)

    def test_a_pipe_in_a_detail_cannot_break_the_findings_table_open(self):
        self.publish(status="fail", findings=[
            {"skill": "a", "kind": "content-drift",
             "detail": "differs in ['pipe|name.md']"}])
        _, body, _ = self.react()
        self.assertIn(r"pipe\|name.md", body,
                      "an unescaped `|` splits the row into extra columns, so "
                      "the finding is still 'present' and reads as garbage")

    def test_a_detail_carrying_an_address_or_an_absolute_path_is_scrubbed(self):
        self.publish(status="fail", findings=[
            {"skill": "a", "kind": "account-copy-missing",
             "detail": "mailed relay@example.net about "
                       "/home/someone/.claude/skills/synced/a"}])
        _, body, _ = self.react()
        self.assertNotIn("relay@example.net", body)
        self.assertNotIn("/home/someone", body)
        # Vacuity controls: the finding must still land, and both scrubbers
        # must be shown to have fired rather than the detail having gone
        # missing altogether.
        self.assertIn("`a`", body)
        self.assertIn("<address>", body)
        self.assertIn("<path>", body)

    def test_a_real_audit_result_publishes_no_path_no_address_no_description(self):
        """End to end over `account_store.audit`, not a hand-written finding.

        The hand-written cases above prove the scrubbers work on the shapes
        somebody thought of. This one runs the real audit against a real fake
        store, so the details are the ones `account_store` actually builds —
        which is where the `$HOME` path comes from in production.
        """
        registry = make_registry(self.root, skills=("fixture-alpha", "fixture-ghost"))
        home = self.root / "home"
        store = home / account_store.MANIFEST_RELPATH.parent
        store.mkdir(parents=True)
        # Reserved domain, per the fleet rule on fixtures. The description is
        # the thing that must not be republished: it is not in the artifact,
        # and it is the only field that decides whether a skill triggers.
        description = ("Ping relay@example.com whenever the quarterly "
                       "reconciliation deck needs rebuilding.")
        write_skill(store / "fixture-alpha", "fixture-alpha", description)
        store.joinpath("manifest.json").write_text(json.dumps({
            "lastUpdated": 0,
            "skills": [{"skillId": name, "name": name, "source": "custom",
                        "description": description,
                        "updatedAt": "2026-05-11T22:23:38.972889Z"}
                       for name in ("fixture-alpha", "fixture-ghost")]}),
            encoding="utf-8")

        result = account_store.audit(home, registry)
        summary = account_store.summarise(
            result, generated_at=NOW.strftime("%Y-%m-%dT%H:%M:%SZ"),
            registry_ref="0" * 40)
        self.assertEqual(summary["status"], "fail")
        self.latest.write_text(json.dumps(summary), encoding="utf-8")

        _, body, line = self.react()
        kinds = {f["kind"] for f in summary["findings"]}
        self.assertIn("account-copy-missing", kinds,
                      "this fixture exists to produce the finding whose detail "
                      "interpolates an absolute directory; without it the "
                      "path assertion below passes vacuously")
        self.assertIn("<path>", body)
        for forbidden in (str(home), "relay@example.com", "reconciliation",
                          description):
            self.assertNotIn(forbidden, body)
        self.assertIsNone(
            re.search(r"[\w.+-]+@[\w-]+\.[A-Za-z]{2,}", body),
            "no address-shaped string may reach a public issue body")
        for skill in ("fixture-alpha", "fixture-ghost"):
            self.assertIn(f"`{skill}`", body)
        self.assertNotIn(str(home), line)


if __name__ == "__main__":
    unittest.main(verbosity=1)
