#!/usr/bin/env python3
"""Which skill copy a local session loaded: the `digest`, `digest_null_reason`,
`base_kind` and `registry` keys of the census's PRIVATE skill records (#536).

Every home, checkout and transcript here is synthetic, written under a
mkdtemp; git remotes are only configured, never contacted; `now` is always
passed in. A file's ctime cannot be set, so a record that must hash is dated
far in the future (FUTURE) and one that must see a change far in the past
(PAST). No network, no clock.
"""

from __future__ import annotations

import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "harness"))
sys.path.insert(0, str(REPO_ROOT / "scripts"))
sys.path.insert(0, str(REPO_ROOT / "test" / "issues"))
import model_usage_census as census  # noqa: E402
import skill_digest  # noqa: E402
from test_issue_skill_usage import ALLOW, write_transcript  # noqa: E402

FUTURE = datetime(2099, 1, 7, 10, 0, 0, tzinfo=timezone.utc)
PAST = datetime(1990, 1, 1, tzinfo=timezone.utc)
#: A census run "now" in FUTURE's week, so FUTURE-dated records are counted.
NOW_FUTURE = datetime(2099, 1, 8, 12, 0, 0, tzinfo=timezone.utc)
NOW_FUTURE_TEXT = "2099-01-08T12:00:00Z"
FIXED_MTIME = datetime(2026, 1, 1, tzinfo=timezone.utc).timestamp()
SKILL = "finding-unknowns"
HEX = "0123456789abcdef" * 4


def git(*args, cwd):
    env = dict(os.environ, GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_NOSYSTEM="1",
               GIT_AUTHOR_NAME="Fixture", GIT_COMMITTER_NAME="Fixture",
               GIT_AUTHOR_EMAIL="fixture@example.com",
               GIT_COMMITTER_EMAIL="fixture@example.com")
    return subprocess.run(["git", *args], cwd=cwd, env=env, check=True,
                          capture_output=True, text=True).stdout.strip()


def make_skill(path: Path, files=None) -> Path:
    """A skill directory with fixed contents and a fixed mtime throughout."""
    files = files or {"SKILL.md": b"---\nname: x\n---\n# A skill\n",
                      "notes/more.md": b"more\n"}
    for relpath, data in files.items():
        target = path / relpath
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
    for item in [path, *path.rglob("*")]:
        os.utime(item, (FIXED_MTIME, FIXED_MTIME), follow_symlinks=False)
    return path


def skill_call(skill, call_id, when="2099-01-07T10:00:00Z", model=None):
    message = {"role": "assistant",
               "content": [{"type": "tool_use", "id": call_id,
                            "name": "Skill", "input": {"skill": skill}}]}
    if model is not None:
        message["model"] = model
    return {"type": "assistant", "timestamp": when, "uuid": f"a-{call_id}",
            "message": message}


def typed(command, uuid, when="2099-01-07T10:00:00Z"):
    return {"type": "user", "timestamp": when, "uuid": uuid,
            "message": {"role": "user", "content":
                        f"<command-message>{command}</command-message>\n"
                        f"<command-name>/{command}</command-name>"}}


def meta(text, when="2099-01-07T10:00:01Z", as_items=True, **links):
    content = [{"type": "text", "text": text}] if as_items else text
    return {"type": "user", "timestamp": when, "isMeta": True, "uuid": "m-1",
            "message": {"role": "user", "content": content}, **links}


def base_text(path) -> str:
    return f"Base directory for this skill: {path}\n\n# A skill\n"


class ResolveTests(unittest.TestCase):
    """`LoadedCopies.resolve` on its own, kind by kind and reason by reason."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="loaded-copy-")).resolve()
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.claude = self.tmp / "home" / ".claude"
        self.copies = census.LoadedCopies()

    def resolve(self, base, name=SKILL, when=FUTURE):
        return self.copies.resolve(name, None if base is None else str(base), when)

    def plugin_skill(self, marketplace="example-mkt") -> Path:
        return make_skill(self.claude / "plugins" / "cache" / marketplace
                          / "example-plugin" / "1.0.0" / "skills" / SKILL)

    def known(self, marketplaces):
        path = self.claude / "plugins" / "known_marketplaces.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(marketplaces), encoding="utf-8")

    def record(self, entries):
        path = self.claude / "skills" / ".skills-bootstrap-installed.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({"version": 1, "installed": entries}),
                        encoding="utf-8")

    def checkout(self, origin=None) -> tuple[Path, Path]:
        work = self.tmp / "checkout"
        skill = make_skill(work / ".claude" / "skills" / SKILL)
        (work / ".gitignore").write_text("*.pyc\n", encoding="utf-8")
        git("init", "-q", cwd=work)
        git("add", ".", cwd=work)
        git("commit", "-q", "-m", "fixture", cwd=work)
        if origin is not None:
            git("remote", "add", "origin", origin, cwd=work)
        (skill / "cache.pyc").write_bytes(b"ignored")
        os.utime(skill / "cache.pyc", (FIXED_MTIME, FIXED_MTIME))
        os.utime(skill, (FIXED_MTIME, FIXED_MTIME))
        return work, skill

    # --- kinds ---------------------------------------------------------------

    def test_plugin_cache_takes_its_registry_from_known_marketplaces(self):
        skill = self.plugin_skill()
        self.known({"example-mkt": {"source": {"source": "github",
                                               "repo": "example-owner/registry"}}})
        self.assertEqual(self.resolve(skill), {
            "digest": skill_digest.lock_digest(skill), "digest_null_reason": None,
            "base_kind": "plugin-cache", "registry": "example-owner/registry"})

    def test_plugin_cache_registry_is_null_unless_a_github_marketplace_names_it(self):
        skill = self.plugin_skill()
        for label, known in (
                ("absent", None),
                ("other marketplace", {"elsewhere": {"source": {
                    "source": "github", "repo": "example-owner/registry"}}}),
                ("directory source", {"example-mkt": {"source": {
                    "source": "directory", "path": "/somewhere"}}}),
                ("git url source", {"example-mkt": {"source": {
                    "source": "git", "url": "https://example.com/r.git"}}}),
                ("not owner/repo", {"example-mkt": {"source": {
                    "source": "github", "repo": "../../etc"}}})):
            with self.subTest(label):
                if known is not None:
                    self.known(known)
                copy = census.LoadedCopies().resolve(SKILL, str(skill), FUTURE)
                self.assertEqual((copy["base_kind"], copy["registry"]),
                                 ("plugin-cache", None))
                self.assertEqual(copy["digest"], skill_digest.lock_digest(skill))

    def test_plugin_cache_guard_covers_only_the_skill_directory(self):
        skill = self.plugin_skill()
        sibling = skill.parent.parent / "README.md"
        sibling.write_text("changed later\n", encoding="utf-8")
        later = datetime(2100, 1, 1, tzinfo=timezone.utc).timestamp()
        os.utime(sibling, (later, later))
        self.assertIsNotNone(self.resolve(skill)["digest"])
        os.utime(skill / "SKILL.md", (later, later))
        self.assertEqual(census.LoadedCopies().resolve(SKILL, str(skill), FUTURE)
                         ["digest_null_reason"], "changed-since-load")

    def test_user_skills_registry_needs_the_install_records_digest(self):
        skill = make_skill(self.claude / "skills" / SKILL)
        digest = skill_digest.lock_digest(skill)
        url = "https://github.com/example-owner/registry"
        for label, entry, registry in (
                ("matching, prefixed", {"digest": "sha256:" + digest, "registry": url}, "example-owner/registry"),
                ("matching, .git", {"digest": digest, "registry": url + ".git"}, "example-owner/registry"),
                ("edited copy", {"digest": HEX, "registry": url}, None),
                ("ssh registry", {"digest": digest, "registry": "git@github.com:example-owner/registry.git"}, None),
                ("other host", {"digest": digest, "registry": "https://example.com/example-owner/registry"}, None),
                ("token in url", {"digest": digest, "registry": "https://x:y@github.com/example-owner/registry"}, None)):
            with self.subTest(label):
                self.record([dict(entry, name=SKILL, bundle="b")])
                self.assertEqual(census.LoadedCopies().resolve(SKILL, str(skill), FUTURE), {
                    "digest": digest, "digest_null_reason": None,
                    "base_kind": "user-skills", "registry": registry})
        self.record([{"name": "another", "digest": digest, "registry": url}])
        self.assertIsNone(census.LoadedCopies().resolve(SKILL, str(skill), FUTURE)["registry"])

    def test_account_sync(self):
        skill = make_skill(self.claude / "skills" / "synced" / "abc_def" / SKILL)
        self.assertEqual(self.resolve(skill), {
            "digest": skill_digest.lock_digest(skill), "digest_null_reason": None,
            "base_kind": "account-sync", "registry": None})

    def test_account_plugin_from_a_cowork_session(self):
        skill = make_skill(self.tmp / "Claude" / "local-agent-mode-sessions"
                           / "skills-plugin" / "abc" / "skills" / SKILL)
        self.assertEqual(self.resolve(skill)["base_kind"], "account-plugin")
        self.assertIsNotNone(self.resolve(skill)["digest"])

    def test_repo_skips_git_ignored_files_and_reads_a_github_origin(self):
        work, skill = self.checkout("git@github.com:example-owner/widgets.git")
        copy = self.resolve(skill)
        self.assertEqual(copy, {
            "digest": skill_digest.lock_digest(skill, skill_digest.git_ignored(work)),
            "digest_null_reason": None, "base_kind": "repo",
            "registry": "example-owner/widgets"})
        self.assertNotEqual(copy["digest"], skill_digest.lock_digest(skill))

    def test_repo_registry_is_null_without_a_github_origin(self):
        for label, origin in (("no origin", None),
                              ("other host", "https://gitlab.example.com/o/r.git"),
                              ("local path", "/srv/git/widgets.git")):
            with self.subTest(label):
                work, skill = self.checkout(origin)
                copy = census.LoadedCopies().resolve(SKILL, str(skill), FUTURE)
                self.assertEqual((copy["base_kind"], copy["registry"]), ("repo", None))
                self.assertIsNotNone(copy["digest"])
                shutil.rmtree(work)

    def test_a_https_github_origin_is_reduced_to_owner_repo(self):
        _, skill = self.checkout("https://github.com/example-owner/widgets.git")
        self.assertEqual(self.resolve(skill)["registry"], "example-owner/widgets")

    def test_builtin_prompt_skills_and_bundled_skills(self):
        for name in sorted(census.BUILTIN_SKILLS):
            self.assertEqual(self.resolve(None, name=name), {
                "digest": None, "digest_null_reason": "builtin",
                "base_kind": "builtin", "registry": None})
        bundled = self.tmp / "bundled-skills" / "2.1.287" / "abc" / "claude-api"
        self.assertEqual(self.resolve(bundled, name="claude-api")["base_kind"], "builtin")
        self.assertEqual(self.resolve(bundled, name="claude-api")["digest_null_reason"],
                         "builtin")

    def test_anything_else_is_outside_known_roots_and_not_hashed(self):
        skill = make_skill(self.tmp / "loose" / SKILL)
        with mock.patch.object(skill_digest, "lock_digest") as digest:
            self.assertEqual(self.resolve(skill), {
                "digest": None, "digest_null_reason": "outside-known-roots",
                "base_kind": "unknown", "registry": None})
            self.assertEqual(self.resolve(f"relative/{SKILL}")["digest_null_reason"],
                             "outside-known-roots")
        digest.assert_not_called()

    # --- null reasons ----------------------------------------------------------

    def test_no_base_dir(self):
        self.assertEqual(self.resolve(None), {
            "digest": None, "digest_null_reason": "no-base-dir",
            "base_kind": "unknown", "registry": None})

    def test_a_base_dir_named_for_another_skill_is_no_base_dir(self):
        skill = make_skill(self.claude / "skills" / "another-skill")
        self.assertEqual(self.resolve(skill)["digest_null_reason"], "no-base-dir")

    def test_bad_names(self):
        skill = make_skill(self.claude / "skills" / SKILL)
        for name in ("a:b:c", "../x", "", ".hidden", "x" * 129, "has space",
                     "plugin:", "/finding-unknowns"):
            with self.subTest(name=name):
                self.assertEqual(self.resolve(skill, name=name)["digest_null_reason"],
                                 "bad-name")
        self.assertEqual(self.resolve(skill, name="some-plugin:" + SKILL)
                         ["digest_null_reason"], None)

    def test_gone(self):
        copy = self.resolve(self.claude / "plugins" / "cache" / "m" / "p" / "1"
                            / "skills" / SKILL)
        self.assertEqual((copy["base_kind"], copy["digest_null_reason"], copy["digest"]),
                         ("plugin-cache", "gone", None))
        self.assertEqual(self.resolve(self.tmp / "nowhere" / SKILL)
                         ["digest_null_reason"], "gone")

    def test_changed_since_load(self):
        skill = make_skill(self.claude / "skills" / SKILL)
        self.assertEqual(self.resolve(skill, when=PAST), {
            "digest": None, "digest_null_reason": "changed-since-load",
            "base_kind": "user-skills", "registry": None})
        self.assertIsNotNone(self.resolve(skill, when=FUTURE)["digest"])

    def test_refused_by_registry_rules(self):
        skill = make_skill(self.claude / "skills" / SKILL)
        (skill / "link").symlink_to("SKILL.md")
        self.assertEqual(self.resolve(skill)["digest_null_reason"],
                         "refused-by-registry-rules")

    def test_too_large(self):
        skill = make_skill(self.claude / "skills" / SKILL)
        with mock.patch.object(skill_digest, "MAX_FILES", 1):
            self.assertEqual(self.resolve(skill)["digest_null_reason"], "too-large")

    def test_every_reason_and_kind_is_in_its_fixed_tuple(self):
        self.assertEqual(len(census.DIGEST_NULL_REASONS), 8)
        self.assertEqual(len(census.BASE_KINDS), 7)
        for name, base in (("simplify", None), (SKILL, None), ("a:b:c", None)):
            copy = self.resolve(base, name=name)
            self.assertIn(copy["digest_null_reason"], census.DIGEST_NULL_REASONS)
            self.assertIn(copy["base_kind"], census.BASE_KINDS)

    # --- caching and paths -----------------------------------------------------

    def test_each_base_dir_is_hashed_once_and_guarded_per_record(self):
        skill = make_skill(self.claude / "skills" / SKILL)
        with mock.patch.object(skill_digest, "lock_digest",
                               wraps=skill_digest.lock_digest) as digest:
            first = self.resolve(skill)
            self.assertEqual(self.resolve(skill), first)
            self.assertEqual(self.resolve(skill, when=PAST)["digest_null_reason"],
                             "changed-since-load")
        self.assertEqual(digest.call_count, 1)

    def test_windows_and_wsl_paths_are_normalized(self):
        self.assertEqual(census.native_path("C:\\Users\\x\\.claude\\skills\\s"),
                         "/mnt/c/Users/x/.claude/skills/s")
        self.assertEqual(census.native_path("d:\\a"), "/mnt/d/a")
        self.assertEqual(census.native_path("\\\\wsl.localhost\\Ubuntu\\home\\x\\s"),
                         "/home/x/s")
        self.assertEqual(census.native_path("\\\\wsl$\\Ubuntu\\home\\x\\s"), "/home/x/s")
        self.assertEqual(census.native_path("/home/x/s"), "/home/x/s")

    def test_the_first_line_rule(self):
        line = census.base_dir_line
        self.assertEqual(line({"content": [{"type": "text", "text": base_text("/a/b")}]}),
                         "/a/b")
        self.assertEqual(line({"content": base_text("/a/b")}), "/a/b")
        self.assertIsNone(line({"content": "Quoting:\n" + base_text("/a/b")}))
        self.assertIsNone(line({"content": " " + base_text("/a/b")}))
        self.assertIsNone(line({"content": [{"type": "image"},
                                            {"type": "text", "text": base_text("/a")}]}))
        self.assertIsNone(line({"content": "Base directory for this skill: "}))
        self.assertIsNone(line({"content": None}))


class LinkingTests(unittest.TestCase):
    """The base directory reaches a record only through its own link."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="loaded-copy-")).resolve()
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.projects = self.tmp / "projects"
        self.skill = make_skill(self.tmp / "home" / ".claude" / "skills" / SKILL)
        self.digest = skill_digest.lock_digest(self.skill)

    def records(self, entries):
        write_transcript(self.projects / "-home-example-proj" / "s.jsonl", entries,
                         mtime=NOW_FUTURE)
        found: list = []
        census.census_all(self.projects, NOW_FUTURE, 8, ALLOW, found)
        return {r["id"]: (r["digest"], r["digest_null_reason"], r["base_kind"])
                for r in found}

    def loaded(self):
        return (self.digest, None, "user-skills")

    def test_a_skill_call_links_by_source_tool_use_id(self):
        self.assertEqual(self.records([
            skill_call(SKILL, "toolu_01"),
            meta(base_text(self.skill), sourceToolUseID="toolu_01", parentUuid="a-toolu_01"),
        ]), {"toolu_01": self.loaded()})

    def test_a_skill_call_does_not_link_by_parent_uuid_or_another_id(self):
        self.assertEqual(self.records([
            skill_call(SKILL, "toolu_01"),
            meta(base_text(self.skill), parentUuid="a-toolu_01"),
            meta(base_text(self.skill), sourceToolUseID="toolu_99"),
        ]), {"toolu_01": (None, "no-base-dir", "unknown")})

    def test_a_typed_command_links_by_parent_uuid_only(self):
        self.assertEqual(self.records([
            typed(SKILL, "u-typed"),
            meta(base_text(self.skill), parentUuid="u-typed", as_items=False),
        ]), {"u-typed": self.loaded()})
        self.assertEqual(self.records([
            typed(SKILL, "u-typed"),
            meta(base_text(self.skill), sourceToolUseID="u-typed"),
        ]), {"u-typed": (None, "no-base-dir", "unknown")})

    def test_only_a_later_entry_marked_is_meta_links(self):
        not_meta = meta(base_text(self.skill), sourceToolUseID="toolu_01")
        del not_meta["isMeta"]
        self.assertEqual(self.records([
            meta(base_text(self.skill), sourceToolUseID="toolu_01"),
            not_meta,
            skill_call(SKILL, "toolu_01"),
            dict(not_meta, isMeta="true"),
        ]), {"toolu_01": (None, "no-base-dir", "unknown")})

    def test_a_base_dir_line_quoted_in_prose_does_not_link(self):
        self.assertEqual(self.records([
            skill_call(SKILL, "toolu_01"),
            meta("As the earlier message said:\n" + base_text(self.skill),
                 sourceToolUseID="toolu_01"),
        ]), {"toolu_01": (None, "no-base-dir", "unknown")})

    def test_a_record_dated_before_the_change_is_changed_since_load(self):
        records = self.records([
            skill_call(SKILL, "toolu_01", when="2099-01-07T10:00:00Z"),
            meta(base_text(self.skill), sourceToolUseID="toolu_01")])
        self.assertEqual(records["toolu_01"], self.loaded())
        os.utime(self.skill / "SKILL.md", (FUTURE.timestamp() + 3600,) * 2)
        records = self.records([
            skill_call(SKILL, "toolu_01", when="2099-01-07T10:00:00Z"),
            meta(base_text(self.skill), sourceToolUseID="toolu_01")])
        self.assertEqual(records["toolu_01"], (None, "changed-since-load", "user-skills"))

    def test_a_built_in_with_no_message_and_a_bad_name(self):
        self.assertEqual(self.records([
            skill_call("simplify", "toolu_01"),
            skill_call("a:b:c", "toolu_02"),
        ]), {"toolu_01": (None, "builtin", "builtin"),
             "toolu_02": (None, "bad-name", "unknown")})

    def test_no_path_reaches_a_record(self):
        write_transcript(self.projects / "p" / "s.jsonl", [
            skill_call(SKILL, "toolu_01"),
            meta(base_text(self.skill), sourceToolUseID="toolu_01")], mtime=NOW_FUTURE)
        found: list = []
        census.census_all(self.projects, NOW_FUTURE, 8, ALLOW, found)
        self.assertNotIn(str(self.tmp), json.dumps(found))
        self.assertEqual(found[0]["digest"], self.digest)


class PublicOutputTests(unittest.TestCase):
    """The loaded-copy keys never reach the public files, and merge keeps
    them as it keeps every other key."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="loaded-copy-")).resolve()
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.projects = self.tmp / "projects"
        self.skill = make_skill(self.tmp / "home" / ".claude" / "skills" / SKILL)
        write_transcript(self.projects / "-home-example-proj" / "s.jsonl", [
            skill_call(SKILL, "toolu_01", model="claude-opus-5"),
            meta(base_text(self.skill), sourceToolUseID="toolu_01"),
            typed("workflow-path-audit", "u-typed"),
            meta(base_text(self.tmp / "gone" / "workflow-path-audit"),
                 parentUuid="u-typed")], mtime=NOW_FUTURE)

    def run_main(self, label, events=True):
        out, weekly = self.tmp / f"{label}.json", self.tmp / f"{label}-weekly.json"
        argv = ["model_usage_census.py", "--projects", str(self.projects),
                "--out", str(out), "--weekly-out", str(weekly),
                "--now", NOW_FUTURE_TEXT, "--hook-logs", ""]
        if events:
            argv += ["--events-out", str(self.tmp / f"{label}-events.jsonl")]
        with mock.patch.object(sys, "argv", argv), redirect_stdout(io.StringIO()):
            self.assertEqual(census.main(), 0)
        return out.read_bytes(), weekly.read_bytes()

    def test_public_outputs_are_byte_identical_with_and_without_resolution(self):
        resolved = self.run_main("resolved")
        lines = (self.tmp / "resolved-events.jsonl").read_text(encoding="utf-8")
        self.assertEqual(
            sorted((r["id"], r["digest_null_reason"]) for r in map(json.loads, lines.splitlines())),
            [("toolu_01", None), ("u-typed", "gone")])
        with mock.patch.object(census.LoadedCopies, "resolve",
                               lambda self, name, base, when: {}):
            unresolved = self.run_main("unresolved")
        self.assertEqual(resolved, unresolved)
        self.assertEqual(resolved, self.run_main("no-events", events=False))
        for key in (b"digest", b"base_kind", b"registry", str(self.tmp).encode()):
            self.assertNotIn(key, resolved[0] + resolved[1])

    def test_merge_accepts_the_new_keys_and_keeps_old_lines_byte_for_byte(self):
        self.run_main("merge")
        store = self.tmp / "store"
        machine = census.machine_name()
        old = store / "events" / "2099-01" / f"{machine}.jsonl"
        old.parent.mkdir(parents=True)
        legacy = ('{"id":"legacy","ts":"2099-01-01T00:00:00.000Z",'
                  '"machine":"%s","kind":"skill","name":"x"}' % machine)
        old.write_text(legacy + "\n", encoding="utf-8")
        self.assertEqual(census.merge_events(self.tmp / "merge-events.jsonl", store), 2)
        lines = old.read_text(encoding="utf-8").splitlines()
        self.assertEqual(lines[0], legacy)
        added = [json.loads(line) for line in lines[1:]]
        self.assertTrue(all({"digest", "digest_null_reason", "base_kind", "registry"}
                            <= set(record) for record in added))


if __name__ == "__main__":
    unittest.main()
