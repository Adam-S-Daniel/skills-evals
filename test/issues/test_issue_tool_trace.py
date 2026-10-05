"""#89: a bounded, redacted tool-call trace beside raw.json.

raw.json keeps only the CLI's result objects, so a run's tool calls could not
be read back when ci-watcher-loops needed diagnosing. `tool_trace.json` keeps
one line per tool call and per tool result. These tests use a canned
`--verbose` message array; no process or network is used.

Every secret-looking string here is assembled at run time, so the source
file itself never carries one for a secret scanner to flag.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "harness"))

import cli_json  # noqa: E402
from cli_json import bounded_tool_trace, redact, secret_values, tool_events  # noqa: E402
import run_eval  # noqa: E402

# A credential the arm's environment carries (eval.yml forwards
# ANTHROPIC_AUTH_TOKEN to the CLI), and one with a well-known token shape.
ENV_SECRET = "fake" + "-bearer-" + "0123456789abcdef"
SHAPED_SECRET = "gh" + "p_" + "A1b2C3d4E5f6G7h8I9j0K1l2M3n4O5p6Q7r8"
ASSIGNED_SECRET = "s3cr3t" + "Value" + "XYZ"

RESULT = {"type": "result", "is_error": False, "result": "done",
          "total_cost_usd": 0.25, "usage": {"input_tokens": 2},
          "num_turns": 3, "duration_ms": 8,
          "modelUsage": {"fake-default-model": {"inputTokens": 2}}}


def verbose_array(result: dict = RESULT) -> list:
    """A `--verbose` message array: init, a Bash call whose result is an
    error, a Read whose output is oversized and leaks secrets, and the
    result."""
    big = ("line\n" * 2000) + ENV_SECRET
    return [
        {"type": "system", "subtype": "init", "cwd": "/home/runner/private-workspace",
         "tools": ["Bash", "Read"]},
        {"type": "assistant", "parent_tool_use_id": None, "message": {"content": [
            {"type": "text", "text": "Watching the run."},
            {"type": "tool_use", "id": "toolu_01", "name": "Bash",
             "input": {"command": "gh run watch 123 --exit-status | tail -5; "
                                  "echo GH_TOKEN=" + ASSIGNED_SECRET + " "
                                  + "x" * 400,
                       "description": "watch"}}]}},
        {"type": "user", "parent_tool_use_id": None, "message": {"content": [
            {"type": "tool_result", "tool_use_id": "toolu_01", "is_error": True,
             "content": "Exit code 1\nauthorization: Bearer " + ENV_SECRET}]}},
        {"type": "assistant", "parent_tool_use_id": "toolu_sub", "message": {"content": [
            {"type": "tool_use", "id": "toolu_02", "name": "Read",
             "input": {"file_path": "/home/runner/private-workspace/.env"}}]}},
        {"type": "user", "parent_tool_use_id": "toolu_sub", "message": {"content": [
            {"type": "tool_result", "tool_use_id": "toolu_02",
             "content": [{"type": "text", "text": "token " + SHAPED_SECRET + "\n" + big}]}]}},
        result,
    ]


def cli_reply(payload: object, returncode: int = 0) -> subprocess.CompletedProcess:
    return subprocess.CompletedProcess(args=["fake-cli"], returncode=returncode,
                                       stdout=json.dumps(payload), stderr="")


class ToolEventTests(unittest.TestCase):
    def setUp(self):
        self.events = tool_events(verbose_array(), [ENV_SECRET])

    def test_one_event_per_call_and_result_in_order(self):
        self.assertEqual([(e["kind"], e["id"]) for e in self.events],
                         [("tool_use", "toolu_01"), ("tool_result", "toolu_01"),
                          ("tool_use", "toolu_02"), ("tool_result", "toolu_02")])
        self.assertEqual(self.events[0]["name"], "Bash")
        self.assertTrue(self.events[0]["input"].startswith("gh run watch 123"))
        self.assertFalse(self.events[0]["subagent"])
        self.assertTrue(self.events[2]["subagent"])

    def test_result_error_flag_and_output_length(self):
        self.assertIs(self.events[1]["is_error"], True)
        self.assertIs(self.events[3]["is_error"], False)
        self.assertTrue(self.events[1]["output"].startswith("Exit code 1"))
        self.assertGreater(self.events[3]["output_chars"], 10000)

    def test_inputs_and_outputs_are_truncated(self):
        self.assertGreater(self.events[0]["input_chars"], cli_json.TRACE_INPUT_CHARS)
        self.assertLessEqual(len(self.events[0]["input"]),
                             cli_json.TRACE_INPUT_CHARS + 3)
        self.assertLessEqual(len(self.events[3]["output"]),
                             cli_json.TRACE_OUTPUT_CHARS + 3)

    def test_secrets_and_paths_are_redacted(self):
        text = json.dumps(self.events)
        for secret in (ENV_SECRET, SHAPED_SECRET, ASSIGNED_SECRET,
                       "private-workspace"):
            self.assertNotIn(secret, text)
        self.assertIn("GH_TOKEN=<redacted>", self.events[0]["input"])
        self.assertEqual(self.events[2]["input"], "<path>")

    def test_a_single_result_object_has_no_events(self):
        self.assertEqual(tool_events(RESULT), [])
        self.assertEqual(tool_events(["junk", {"type": "assistant"}]), [])


class RedactionTests(unittest.TestCase):
    def test_env_values_named_as_credentials_are_collected(self):
        env = {"ANTHROPIC_AUTH_TOKEN": ENV_SECRET, "PATH": "/usr/bin:/bin",
               "GH_TOKEN": "short", "LANG": "C.UTF-8"}
        self.assertEqual(secret_values(env), [ENV_SECRET])

    def test_credential_shapes_are_redacted_without_a_known_value(self):
        for text in (SHAPED_SECRET, "API_KEY=" + ASSIGNED_SECRET,
                     '"password": "' + ASSIGNED_SECRET + '"',
                     "sk-" + "ant-" + "a" * 30):
            with self.subTest(text=text[:12]):
                self.assertIn("<redacted>", redact(text))
                self.assertNotIn(ASSIGNED_SECRET, redact(text))


class BoundTests(unittest.TestCase):
    def test_trace_is_capped_and_counts_what_it_dropped(self):
        calls = [tool_events(verbose_array(), [ENV_SECRET]) for _ in range(200)]
        trace = bounded_tool_trace(calls, max_bytes=4096)
        size = sum(len(json.dumps(e).encode("utf-8")) for e in trace["events"])
        self.assertLessEqual(size, 4096)
        self.assertGreater(trace["omitted_events"], 0)
        self.assertEqual(len(trace["events"]) + trace["omitted_events"], 800)
        self.assertEqual(trace["schema_version"], 1)
        self.assertEqual(trace["calls"], 200)

    def test_default_cap_holds_for_a_long_run(self):
        calls = [tool_events(verbose_array(), [ENV_SECRET]) for _ in range(500)]
        trace = bounded_tool_trace(calls)
        self.assertLessEqual(len(json.dumps(trace).encode("utf-8")),
                             cli_json.TRACE_MAX_BYTES + 1024)
        self.assertGreater(trace["omitted_events"], 0)


class RunAgentTraceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.workspace = Path(self.temp.name)
        home = self.workspace / "home"
        home.mkdir()
        self.env = {"PATH": os.environ["PATH"], "HOME": str(home),
                    "TMPDIR": str(self.workspace), "LANG": "C.UTF-8",
                    "ANTHROPIC_AUTH_TOKEN": ENV_SECRET,
                    "CLAUDE_BIN": str(self.workspace / "no-cli")}

    def _agent(self, reply: subprocess.CompletedProcess) -> dict:
        with mock.patch.dict(os.environ, self.env, clear=True), \
                mock.patch("subprocess.run", return_value=reply):
            return run_eval.run_agent(self.workspace, "prompt",
                                      {"name": "without_skill", "timeout": 5})

    def test_scoring_inputs_are_unchanged(self):
        traced = self._agent(cli_reply(verbose_array()))
        plain = self._agent(cli_reply(RESULT))
        self.assertEqual(traced["raw"], RESULT)
        for key in ("transcript", "usage", "cost_usd", "num_turns",
                    "duration_ms", "raw"):
            self.assertEqual(traced[key], plain[key], key)
        self.assertNotIn("tool_trace", plain)
        self.assertEqual(len(traced["tool_trace"]["events"]), 4)

    def test_the_child_envs_credential_is_redacted(self):
        trace = self._agent(cli_reply(verbose_array()))["tool_trace"]
        self.assertNotIn(ENV_SECRET, json.dumps(trace))

    def test_a_failed_run_still_keeps_its_trace(self):
        answer = self._agent(cli_reply(verbose_array(RESULT | {"is_error": True}), 1))
        self.assertEqual(answer["error"], "nonzero_exit")
        self.assertEqual(answer["tool_trace"]["events"][1]["is_error"], True)

    def test_written_beside_raw_json_and_raw_json_unchanged(self):
        answer = self._agent(cli_reply(verbose_array()))
        run_eval._write_summary(self.workspace, "fixture", "without_skill",
                                "20261005T000000Z", None, None, None, None,
                                answer["raw"], tool_trace=answer["tool_trace"])
        transcripts = (self.workspace / "fixture" / "20261005T000000Z"
                       / "without_skill" / "transcripts")
        self.assertEqual(json.loads((transcripts / "raw.json").read_text()), RESULT)
        saved = (transcripts / run_eval.TOOL_TRACE_NAME).read_text()
        self.assertEqual(json.loads(saved), answer["tool_trace"])
        for secret in (ENV_SECRET, SHAPED_SECRET, ASSIGNED_SECRET):
            self.assertNotIn(secret, saved)


if __name__ == "__main__":
    unittest.main()
