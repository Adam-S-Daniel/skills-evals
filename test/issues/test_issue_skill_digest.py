#!/usr/bin/env python3
"""The lock-kind skill digest: `harness/skill_digest.py` (#536).

`VECTOR_ALL_FILES` and `VECTOR_GIT_IGNORED_SKIPPED` are the digests of the
tree `build_vector_tree` writes, without and with git's ignored files
skipped. Other repositories commit the same two constants for the same tree,
so a change to either is a change to the digest every `skills.lock` names.
When an adam-agentskills checkout is found (beside this repo, or at
~/repos/adam-agentskills), its generator's own `digest_skill_dir` must give
them too. Every tree is written under a mkdtemp with explicit contents; no
network, no clock.
"""

from __future__ import annotations

import ast
import importlib.util
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "harness"))
import skill_digest  # noqa: E402

VECTOR_ALL_FILES = "681c4d1df407b995d4a9b9d2dbf56a701aed027ce41258fd2868092f1997b4f2"
VECTOR_GIT_IGNORED_SKIPPED = "800541b28e245722ce9d8d6a6e69223ae8359b7b818a64c344ef060af52e2096"


#: Precomposed (NFC) `e` with acute, written as an escape so the source's own
#: normalization cannot change the bytes of the name.
NON_ASCII_NAME = "donn\u00e9es.md"


def git(*args, cwd):
    env = dict(os.environ, GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_NOSYSTEM="1",
               GIT_AUTHOR_NAME="Fixture", GIT_COMMITTER_NAME="Fixture",
               GIT_AUTHOR_EMAIL="fixture@example.com",
               GIT_COMMITTER_EMAIL="fixture@example.com")
    return subprocess.run(["git", *args], cwd=cwd, env=env, check=True,
                          capture_output=True, text=True).stdout


def build_vector_tree(work: Path) -> Path:
    """The test vector: `skill/` inside the git work tree `work`, with a
    nested file, a NUL byte, a non-ASCII name, an empty file, an untracked
    ignored file and a tracked file that matches an ignore rule (force-added).
    The tree is a subdirectory so that `.git` is not part of it."""
    root = work / "skill"
    files = {
        ".gitignore": b"__pycache__/\n*.log\n",
        "SKILL.md": b"---\nname: vector\n---\n# Vector\n",
        "a/b/c.txt": b"nested\n",
        "has-nul-byte.bin": b"before\x00after",  # never `nul.*`: a Windows device name
        NON_ASCII_NAME: "caf\u00e9\n".encode("utf-8"),
        "empty.txt": b"",
        "__pycache__/x.pyc": b"\x00compiled",
        "build/keep.log": b"kept though ignored\n",
    }
    for relpath, data in files.items():
        path = root / relpath
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    git("init", "-q", cwd=work)
    # `add .` rather than naming each file: Windows git mangles a
    # non-ASCII argv entry. The ignore rules leave out exactly the two
    # ignored paths, and the force-add below brings one of them back.
    git("add", ".", cwd=root)
    git("add", "-f", "build/keep.log", cwd=root)
    git("commit", "-q", "-m", "vector", cwd=work)
    return root


def agentskills_generator():
    """adam-agentskills' scripts/generate_skills_lock.py, imported, or None."""
    for checkout in (REPO_ROOT.parent / "adam-agentskills",
                     Path.home() / "repos" / "adam-agentskills"):
        script = checkout / "scripts" / "generate_skills_lock.py"
        if script.is_file():
            spec = importlib.util.spec_from_file_location(
                "agentskills_generate_skills_lock", script)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            return module
    return None


def guidance_hook_test():
    """_agent-guidance's test/test_guidance_load_record.py, or None."""
    for checkout in (REPO_ROOT.parent / "_agent-guidance",
                     Path.home() / "repos" / "_agent-guidance"):
        script = checkout / "test" / "test_guidance_load_record.py"
        if script.is_file():
            return script
    return None


def literal_set_assignment(source: str, name: str) -> frozenset:
    """The set literal assigned to the module-level `name` in `source`,
    read with `ast` (the hook test is not imported: it runs the hook)."""
    for node in ast.parse(source).body:
        if (isinstance(node, ast.Assign)
                and any(isinstance(t, ast.Name) and t.id == name
                        for t in node.targets)):
            return frozenset(ast.literal_eval(node.value))
    raise LookupError(f"no module-level assignment to {name}")


class CloudShardKeysTests(unittest.TestCase):
    """The hook's shard keys and the census reader's `CLOUD_KEYS` are two
    copies of one list: a line with any other key set is skipped by the
    reader, so a key added or renamed on one side silently drops every
    cloud line (skills-evals#726)."""

    def test_the_literal_reader_finds_a_set_and_names_a_missing_one(self):
        source = 'OTHER = 1\nKEYS = {"a", "b"}\n'
        self.assertEqual(literal_set_assignment(source, "KEYS"), {"a", "b"})
        with self.assertRaises(LookupError):
            literal_set_assignment(source, "MISSING")

    def test_the_hook_test_shard_keys_equal_the_census_cloud_keys(self):
        script = guidance_hook_test()
        if script is None:
            reason = ("no _agent-guidance checkout beside this repo or at "
                      "~/repos/_agent-guidance: skipping the cloud shard "
                      "key agreement check")
            print(reason)
            self.skipTest(reason)
        sys.path.insert(0, str(REPO_ROOT / "scripts"))
        try:
            import model_usage_census as census
        finally:
            sys.path.pop(0)
        self.assertEqual(
            literal_set_assignment(script.read_text(encoding="utf-8"),
                                   "SHARD_KEYS"),
            frozenset(census.CLOUD_KEYS))


class VectorTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp(prefix="skill-digest-"))
        cls.tree = build_vector_tree(cls.tmp)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def test_the_ignored_set_is_exactly_the_untracked_ignored_file(self):
        self.assertEqual(skill_digest.git_ignored(self.tree),
                         frozenset({str(self.tree.resolve() / "__pycache__" / "x.pyc")}))

    def test_the_vector_with_every_file(self):
        self.assertEqual(skill_digest.lock_digest(self.tree), VECTOR_ALL_FILES)

    def test_the_vector_with_git_ignored_files_skipped(self):
        self.assertEqual(skill_digest.lock_digest(
            self.tree, skip=skill_digest.git_ignored(self.tree)),
            VECTOR_GIT_IGNORED_SKIPPED)

    def test_mtimes_do_not_enter_the_digest(self):
        for path in self.tree.rglob("*"):
            os.utime(path, (1_000_000_000, 1_000_000_000))
        self.assertEqual(skill_digest.lock_digest(self.tree), VECTOR_ALL_FILES)

    def test_the_generator_in_adam_agentskills_gives_the_same_constants(self):
        generator = agentskills_generator()
        if generator is None:
            reason = ("no adam-agentskills checkout beside this repo or at "
                      "~/repos/adam-agentskills — skipping the cross-repo "
                      "digest agreement check")
            print(reason)
            self.skipTest(reason)
        self.assertEqual(generator.digest_skill_dir(self.tree), VECTOR_ALL_FILES)
        self.assertEqual(generator.digest_skill_dir(
            self.tree, skip=generator.ignored_paths(self.tree)),
            VECTOR_GIT_IGNORED_SKIPPED)


class RefusalTests(unittest.TestCase):

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="skill-digest-"))
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.tree = self.tmp / "skill"
        self.tree.mkdir()
        (self.tree / "SKILL.md").write_bytes(b"# skill\n")

    def test_a_symlinked_root_is_refused(self):
        link = self.tmp / "link"
        link.symlink_to(self.tree, target_is_directory=True)
        with self.assertRaises(skill_digest.DigestRefused):
            skill_digest.lock_digest(link)

    def test_a_symlink_inside_is_refused_whatever_it_points_at(self):
        for target in ("SKILL.md", str(self.tmp), "missing"):
            with self.subTest(target=target):
                link = self.tree / "link"
                link.symlink_to(target)
                with self.assertRaises(skill_digest.DigestRefused):
                    skill_digest.lock_digest(self.tree)
                link.unlink()

    def test_a_fifo_is_refused_not_read(self):
        os.mkfifo(self.tree / "pipe")
        with self.assertRaises(skill_digest.DigestRefused):
            skill_digest.lock_digest(self.tree)

    def test_a_missing_directory_is_an_os_error(self):
        with self.assertRaises(OSError):
            skill_digest.lock_digest(self.tmp / "gone")

    def test_too_many_files(self):
        nested = self.tree / "many"
        nested.mkdir()
        for index in range(skill_digest.MAX_FILES):
            (nested / f"{index}.txt").write_bytes(b"")
        with self.assertRaises(skill_digest.DigestTooLarge):
            skill_digest.lock_digest(self.tree)
        (self.tree / "SKILL.md").unlink()
        self.assertEqual(len(skill_digest.lock_digest(self.tree)), 64)

    def test_too_many_bytes_counted_as_read(self):
        half = skill_digest.MAX_BYTES // 2
        (self.tree / "one.bin").write_bytes(b"\0" * half)
        self.assertEqual(len(skill_digest.lock_digest(self.tree)), 64)
        (self.tree / "two.bin").write_bytes(b"\0" * half)
        with self.assertRaises(skill_digest.DigestTooLarge):
            skill_digest.lock_digest(self.tree)

    def test_normalize_strips_exactly_one_prefix(self):
        hexd = "ab" * 32
        self.assertEqual(skill_digest.normalize(hexd), hexd)
        self.assertEqual(skill_digest.normalize("sha256:" + hexd), hexd)
        self.assertEqual(skill_digest.normalize("sha256:sha256:" + hexd), "sha256:" + hexd)


if __name__ == "__main__":
    unittest.main()
