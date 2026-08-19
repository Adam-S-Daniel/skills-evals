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

import contextlib
import io
import json
import os
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
        # The message must name BOTH causes of staleness, because the verdict
        # cannot distinguish them: the Routine stopped, or it ran and its
        # result never reached eval-results. Blaming the schedule alone sends
        # the reader to check a trigger that is perfectly healthy — 2026-08-14,
        # when three runs fired, measured correctly, and had every push refused.
        ok, status, message = self.verdict(self._summary(days_ago=11))
        self.assertFalse(ok)
        self.assertEqual(status, "stale")
        self.assertIn("stopped firing", message)
        self.assertIn("no longer reaching eval-results", message)
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


if __name__ == "__main__":
    unittest.main(verbosity=1)
