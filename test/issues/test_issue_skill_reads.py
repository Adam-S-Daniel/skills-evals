#!/usr/bin/env python3
"""Read uses (Adam, 2026-11-15): a session that reads `SKILL.md`, or any other
file inside an INSTALLED copy of a skill, used that skill even with no Skill
call. The census counts these as `skill-read` rows, apart from the calls, on
the local surface (transcripts) and the cloud one (the Stop hook's
`skill-read` shard lines), and the removal and explorer readers add them.

Every transcript, store and path here is synthetic, under a mkdtemp; `now` is
always passed in. Each "does not count" test has a control that does count,
so a pass means the rule fired, not that the walk saw nothing.
"""

from __future__ import annotations

import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "harness"))
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "test" / "issues"))
import ingest_usage_sink as sink  # noqa: E402
import model_usage_census as census  # noqa: E402
import skill_usage  # noqa: E402
# Modules, never their TestCase classes by name (test/run_tests.py's
# suite-coverage check rejects a class collected twice).
import test_issue_562_cloud_records as cr562  # noqa: E402
import test_issue_skill_usage as su  # noqa: E402

NOW = su.NOW                                     # 2026-09-04, ISO week 2026-W36
SKILL = "finding-unknowns"                       # in su.ALLOW
INSTALLED = f"/home/example/.claude/skills/{SKILL}/SKILL.md"
CHECKOUT = f"/home/example/repos/adam-agentskills/plugins/adam-anything-anywhere/skills/{SKILL}/SKILL.md"
SESSION_ID = "11111111-2222-3333-4444-555555555555"
START = census.window_from(NOW, 8)


def tool(name, call_id="toolu_r1", when="2026-09-03T10:00:00Z", session=SESSION_ID, **given):
    """One assistant entry holding one tool_use."""
    return {"type": "assistant", "timestamp": when, "sessionId": session,
            "message": {"role": "assistant",
                        "content": [{"type": "tool_use", "id": call_id, "name": name,
                                     "input": given}]}}


def read(path=INSTALLED, **kw):
    return tool("Read", file_path=path, **kw)


def call(skill=SKILL, **kw):
    return {**su.skill_call(skill, **{k: v for k, v in kw.items() if k != "session"}),
            "sessionId": kw.get("session", SESSION_ID)}


class SkillReadsTests(unittest.TestCase):
    """Which tool inputs name an installed copy."""

    def names(self, item, private=frozenset()):
        return census.skill_reads(item["message"]["content"][0], private)

    def test_an_installed_user_skill_read_names_the_skill(self):
        self.assertEqual(self.names(read()), [(SKILL, False)])
        self.assertEqual(self.names(read(f"~/.claude/skills/{SKILL}/references/x.md")),
                         [(SKILL, False)])

    def test_a_plugin_copy_names_the_skill_and_a_private_plugin_is_marked(self):
        cache = f"/home/example/.claude/plugins/cache/adam-agentskills/adam-anything-anywhere/1.2.0/skills/{SKILL}/SKILL.md"
        clone = f"/home/example/.claude/plugins/marketplaces/m/plugins/p/skills/{SKILL}/SKILL.md"
        self.assertEqual(self.names(read(cache)), [(SKILL, False)])
        self.assertEqual(self.names(read(clone)), [(SKILL, False)])
        self.assertEqual(self.names(read(cache), frozenset({"adam-anything-anywhere"})),
                         [(SKILL, True)])

    def test_a_registry_checkout_is_not_an_installed_copy(self):
        self.assertEqual(self.names(read(CHECKOUT)), [])
        self.assertEqual(self.names(tool("Bash", command=f"cat {CHECKOUT}")), [])

    def test_glob_grep_bash_and_windows_paths_are_read_uses(self):
        self.assertEqual(self.names(tool("Glob", path=f"~/.claude/skills/{SKILL}", pattern="*")),
                         [(SKILL, False)])
        self.assertEqual(self.names(tool("Grep", path=f"/root/.claude/skills/{SKILL}/")),
                         [(SKILL, False)])
        self.assertEqual(self.names(tool("Bash", command=f"ls ~/.claude/skills/{SKILL} && echo")),
                         [(SKILL, False)])
        self.assertEqual(self.names(read(f"C:\\Users\\example\\.claude\\skills\\{SKILL}\\SKILL.md")),
                         [(SKILL, False)])

    def test_other_tools_and_the_bare_skills_directory_are_not(self):
        self.assertEqual(self.names(tool("Edit", file_path=INSTALLED)), [])
        self.assertEqual(self.names(tool("Bash", command="ls ~/.claude/skills/")), [])
        self.assertEqual(self.names(tool("Glob", pattern="~/.claude/skills/*/SKILL.md")), [])


    def test_a_command_that_only_mentions_writes_or_fetches_a_copy_is_not_a_read(self):
        # Review findings, 2026-11-15: each of these counted before.
        home = "~/.claude/skills"
        for command in (f"git commit -m 'fix {home}/{SKILL}/SKILL.md'",
                        f"echo {INSTALLED}",
                        f"cat > /tmp/x <<'EOF'\nsee {INSTALLED}\nEOF",
                        f'mkdir -p "$ws/.claude/skills/{SKILL}" && cp -r a {home}/{SKILL}',
                        f"rm -rf {home}/{SKILL}",
                        f"sed -i s/a/b/ {INSTALLED}",
                        f"cat a > {INSTALLED}",
                        f"curl https://example.com/o/r/main/.claude/skills/{SKILL}/SKILL.md",
                        f"cat ./.claude/skills/{SKILL}/SKILL.md",
                        f"cat {home}/README.md"):
            with self.subTest(command=command):
                self.assertEqual(self.names(tool("Bash", command=command)), [])
        # Controls: a reading program, a pipeline, a skill script run.
        self.assertEqual(self.names(tool("Bash", command=f"cat {INSTALLED} | head -5")),
                         [(SKILL, False)])
        self.assertEqual(self.names(tool(
            "Bash", command=f"cd /tmp && python3 {home}/{SKILL}/scripts/x.py arg")),
            [(SKILL, False)])

    def test_an_account_synced_copy_is_keyed_by_its_own_name(self):
        synced = f"/home/example/.claude/skills/synced/{SKILL}/SKILL.md"
        self.assertEqual(self.names(read(synced)), [(SKILL, False)])

    def test_a_malformed_tool_name_is_no_read_and_no_crash(self):
        item = read()
        item["message"]["content"][0]["name"] = ["Read"]
        self.assertEqual(self.names(item), [])

class LocalReadTests(unittest.TestCase):

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="skill-reads-"))
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.projects = self.tmp / "projects"

    def census(self, *transcripts):
        for index, entries in enumerate(transcripts):
            # A (relative path, entries) pair names its file; a bare list gets one.
            rel, body = entries if isinstance(entries, tuple) else (f"s{index}.jsonl", entries)
            su.write_transcript(self.projects / "-home-example-proj" / rel, body)
        self.tally = census.census_all(self.projects, NOW, 8, su.ALLOW)[1]
        return self.tally

    def doc(self):
        return census.build_weekly_document(self.tally, NOW, 8)

    def test_a_read_with_no_skill_call_is_one_skill_read_row(self):
        tally = self.census([read(), read(call_id="toolu_r2", when="2026-09-03T11:00:00Z")])
        self.assertEqual(tally["reads"], {SKILL: {"2026-W36": 1}})
        self.assertEqual(tally["invocations"], {})
        rows = [r for r in self.doc()["rows"] if r["kind"] in ("skill", "skill-read")]
        self.assertEqual(rows, [skill_usage.read_row("2026-08-31", SKILL, 1)])

    def test_two_sessions_reading_are_two_uses_in_the_week_of_their_first_read(self):
        tally = self.census([read()], [read(session="other-session",
                                            when="2026-08-27T10:00:00Z"),
                                       read(session="other-session", call_id="toolu_r9")])
        self.assertEqual(tally["reads"], {SKILL: {"2026-W36": 1, "2026-W35": 1}})

    def test_a_registry_checkout_read_is_not_counted(self):
        tally = self.census([read(CHECKOUT)], [read(session="control")])
        self.assertEqual(tally["reads"], {SKILL: {"2026-W36": 1}})   # the control only

    def test_a_session_that_also_called_the_skill_counts_only_the_call(self):
        tally = self.census([read(), call(call_id="toolu_c1")], [read(session="control")])
        self.assertEqual(tally["invocations"], {SKILL: {"2026-W36": 1}})
        self.assertEqual(tally["reads"], {SKILL: {"2026-W36": 1}})   # the control only

    def test_a_call_in_the_main_transcript_suppresses_a_subagent_read(self):
        # A subagent transcript carries its parent's sessionId.
        tally = self.census(("main.jsonl", [call(call_id="toolu_c1")]),
                            ("main/subagents/agent-1.jsonl", [read()]))
        self.assertEqual(tally["reads"], {})
        self.assertEqual(tally["invocations"], {SKILL: {"2026-W36": 1}})

    def test_a_typed_command_suppresses_the_read_too(self):
        tally = self.census([{**su.typed(f"<command-name>/{SKILL}</command-name>"),
                              "sessionId": SESSION_ID}, read()])
        self.assertEqual(tally["reads"], {})

    def test_an_unlisted_skill_read_counts_under_other(self):
        tally = self.census([read("/home/example/.claude/skills/client-secret-skill/SKILL.md")])
        self.assertEqual(tally["reads"], {"other": {"2026-W36": 1}})

    def test_the_published_rows_carry_no_path_or_session(self):
        self.census([read()])
        text = json.dumps(self.doc())
        for leak in ("/home/example", ".claude", SESSION_ID, "toolu_r1", "SKILL.md"):
            self.assertNotIn(leak, text)


class CloudReadTests(cr562.StoreCase):

    def read_line(self, **overrides):
        return cr562.cloud_line(**{"kind": "skill-read", "id": "toolu_read_01", **overrides})

    def plan(self, local_ids=frozenset()):
        cloud = census.cloud_digest_plan(census.cloud_skill_records(self.store), set(local_ids),
                                         census.store_digests(self.store), START, NOW, su.ALLOW)
        return {"from": START.strftime(skill_usage.STAMP), "uses": [], "registries": [],
                **({"cloud": cloud} if cloud is not None else {})}

    def rows(self, plan, kind):
        rows, _ = census.digest_rows(plan, cr562.ENTRIES, {})
        return sorted((r["week"], r["name"], r["invocations"], r["sessions"])
                      for r in rows if r["kind"] == kind and r["surface"] == "cloud")

    def test_ingest_and_the_census_accept_a_read_line_but_no_other_kind(self):
        self.assertTrue(sink.skill_line_ok(self.read_line()))
        self.assertTrue(census._cloud_line_ok(self.read_line(), "2026-09", cr562.SID))
        self.assertFalse(sink.skill_line_ok(self.read_line(kind="skill-reads")))
        self.assertGreaterEqual(sink.VALIDATOR_VERSION, 5)

    def test_a_read_line_becomes_a_cloud_skill_read_row_not_a_copy_row(self):
        self.shard(self.read_line(), self.read_line(id="toolu_read_02"))   # one session
        self.shard(self.read_line(session=cr562.SID2), sid=cr562.SID2)
        plan = self.plan()
        self.assertEqual(self.rows(plan, "skill-read"), [("2026-08-31", SKILL, 2, 2)])
        self.assertEqual(self.rows(plan, "skill-digest"), [])
        self.assertEqual(census.store_digests(self.store), {})
        doc = skill_usage.document([], NOW, START, 0)
        census.add_digest_rows(doc, plan, census.digest_rows(plan, cr562.ENTRIES, {})[0], NOW)
        self.assertEqual([s["events_scanned"] for s in doc["sources"]
                          if s.get("scope") == "skill-records" and s["surface"] == "cloud"], [0])

    def test_a_read_line_whose_session_has_a_skill_line_for_the_name_is_dropped(self):
        self.shard(self.read_line(), cr562.cloud_line(id="toolu_call_01",
                                                      ts="2026-09-03T10:00:00.000Z"))
        self.shard(self.read_line(session=cr562.SID2), sid=cr562.SID2)   # control
        plan = self.plan()
        self.assertEqual(self.rows(plan, "skill-read"), [("2026-08-31", SKILL, 1, 1)])
        self.assertEqual(self.rows(plan, "skill-digest"), [("2026-08-31", SKILL, 1, 1)])

    def test_a_read_also_seen_locally_counts_once_as_local(self):
        self.shard(self.read_line())
        self.assertEqual(self.rows(self.plan({"toolu_read_01"}), "skill-read"), [])
        self.assertEqual(self.rows(self.plan(), "skill-read"), [("2026-08-31", SKILL, 1, 1)])

    def test_a_plan_written_before_reads_has_none(self):
        plan = {"from": START.strftime(skill_usage.STAMP), "uses": [], "registries": [],
                "cloud": {"from": START.strftime(skill_usage.STAMP), "uses": []}}
        self.assertEqual(census.digest_rows(plan, cr562.ENTRIES, {})[0], [])


class ReaderTests(unittest.TestCase):
    """Removal sums and the public gate count read uses."""

    def doc(self, *rows):
        return {"generated_at": "2026-09-04T06:00:00Z", "schema": 1,
                "sources": [{"surface": "local", "scope": "transcripts",
                             "from": "2026-07-13T00:00:00Z", "to": "2026-09-04T06:00:00Z",
                             "sessions_scanned": 9, "skill_keys": [SKILL]}],
                "rows": list(rows)}

    def test_weight_adds_reads_on_every_surface(self):
        doc = self.doc(su.published_row("2026-08-31", SKILL, 2),
                       skill_usage.read_row("2026-08-31", SKILL, 1),
                       skill_usage.read_row("2026-08-31", SKILL, 3, skill_usage.SURFACE_CLOUD))
        self.assertEqual(skill_usage.weight(doc, SKILL, NOW), 6)

    def test_a_skill_used_only_by_reading_has_a_recorded_use(self):
        doc = self.doc(skill_usage.read_row("2026-08-31", SKILL, 1))
        self.assertTrue(skill_usage.has_recorded_use(doc, SKILL, NOW, surfaces=()))
        self.assertFalse(skill_usage.has_recorded_use(self.doc(), SKILL, NOW, surfaces=()))

    def test_load_accepts_a_read_row(self):
        path = Path(tempfile.mkdtemp(prefix="skill-reads-load-")) / "weekly.json"
        self.addCleanup(shutil.rmtree, path.parent, ignore_errors=True)
        path.write_text(json.dumps(self.doc(skill_usage.read_row("2026-08-31", SKILL, 1))))
        self.assertIsNotNone(skill_usage.load(path))

    def test_the_public_gate_holds_read_names_to_the_allowlist(self):
        ok = self.doc(skill_usage.read_row("2026-08-31", SKILL, 1))
        self.assertEqual(skill_usage.check_public(ok, {SKILL}, set()), [])
        bad = self.doc(skill_usage.read_row("2026-08-31", "client-secret-skill", 1))
        self.assertEqual(skill_usage.check_public(bad, {SKILL}, set()),
                         ["a skill name outside the allowlist"])

    def test_a_failed_store_fetch_carries_the_cloud_read_rows(self):
        previous = self.doc(skill_usage.read_row("2026-08-31", SKILL, 2, skill_usage.SURFACE_CLOUD))
        previous["sources"].append(skill_usage.digest_source(START, NOW, 0,
                                                             skill_usage.SURFACE_CLOUD))
        new = skill_usage.document([], NOW, START, 0)
        self.assertEqual(skill_usage.carry(previous, new)["cloud skill copies"], 1)
        self.assertEqual([r["kind"] for r in new["rows"]], ["skill-read"])


if __name__ == "__main__":
    unittest.main()
