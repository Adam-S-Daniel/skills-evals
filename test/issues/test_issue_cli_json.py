"""The headless CLI may return one result object or a message array."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "harness"))
sys.path.insert(0, str(ROOT / "scripts"))

from cli_json import normalize_cli_result  # noqa: E402
import run_canary  # noqa: E402
import run_eval  # noqa: E402
import propose_skill_edit  # noqa: E402
from scorers import judge  # noqa: E402


RESULT = {"type": "result", "is_error": False, "result": "done",
          "total_cost_usd": 0.25, "usage": {"input_tokens": 2},
          "num_turns": 1, "duration_ms": 8,
          "modelUsage": {"fake-default-model": {"inputTokens": 2}}}
MESSAGE = {"type": "assistant", "message": {"content": []}}


def cli_reply(payload: object) -> subprocess.CompletedProcess:
    """A fake completed CLI invocation; no process or network is used."""
    return subprocess.CompletedProcess(args=["fake-cli"], returncode=0,
                                       stdout=json.dumps(payload), stderr="")


class CliJsonShapeTests(unittest.TestCase):
    def test_dict_is_the_same_object(self):
        legacy = {"result": "done", "is_error": False, "usage": {"input_tokens": 2}}
        before = json.dumps(legacy, separators=(",", ":")).encode()
        self.assertIs(normalize_cli_result(legacy), legacy)
        self.assertEqual(json.dumps(legacy, separators=(",", ":")).encode(), before)

    def test_array_with_result_last(self):
        self.assertIs(normalize_cli_result([MESSAGE, RESULT]), RESULT)

    def test_array_with_result_not_last(self):
        self.assertIs(normalize_cli_result([RESULT, MESSAGE]), RESULT)

    def test_array_without_result(self):
        with self.assertRaisesRegex(ValueError, "exactly one result object"):
            normalize_cli_result([MESSAGE])

    def test_array_with_two_results(self):
        with self.assertRaisesRegex(ValueError, "exactly one result object"):
            normalize_cli_result([RESULT, RESULT])

    def test_array_with_error_result(self):
        error = RESULT | {"is_error": True, "result": "failed"}
        self.assertIs(normalize_cli_result([MESSAGE, error]), error)

    def test_empty_array(self):
        with self.assertRaisesRegex(ValueError, "exactly one result object"):
            normalize_cli_result([])

    def test_non_dict_element_and_scalar_are_rejected_without_echoing_content(self):
        for payload in (["private payload", RESULT], [RESULT, "private payload"],
                        "private payload", None, True, 2):
            with self.subTest(payload=type(payload).__name__):
                with self.assertRaises(ValueError) as caught:
                    normalize_cli_result(payload)
                self.assertNotIn("private payload", str(caught.exception))


class CliJsonConsumersTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.workspace = Path(self.temp.name)

    def _agent(self, payload: object) -> dict:
        with mock.patch("subprocess.run", return_value=cli_reply(payload)):
            return run_eval.run_agent(self.workspace, "prompt",
                                      {"name": "without_skill", "timeout": 5})

    def _canary(self, payload: object) -> dict:
        with mock.patch("subprocess.run", return_value=cli_reply(payload)):
            return run_canary.run_leg(self.workspace, "prompt", "Read", model=None,
                                      timeout=5)

    def _judge(self, payload: object) -> tuple[str, list]:
        with mock.patch("subprocess.run", return_value=cli_reply(payload)):
            with judge.collecting_models() as models:
                text = judge._run_judge_cli("prompt", model=None, timeout=5)
        return text, models

    def _proposal(self, payload: object) -> str:
        with mock.patch("subprocess.run", return_value=cli_reply(payload)):
            return propose_skill_edit.Runner().propose("prompt", "fake-default-model")

    def test_agent_dict_unchanged_and_array_result_last_or_earlier(self):
        for payload in (RESULT, [MESSAGE, RESULT], [RESULT, MESSAGE]):
            with self.subTest(payload=type(payload).__name__):
                answer = self._agent(payload)
                self.assertEqual(answer["transcript"], "done")
                self.assertEqual(answer["cost_usd"], 0.25)
                self.assertEqual(answer["usage"], {"input_tokens": 2})
                self.assertEqual(answer["raw"], RESULT)
                self.assertEqual(run_eval.models_used(answer["raw"]),
                                 ["fake-default-model"])

    def test_agent_array_error_and_invalid_shapes(self):
        error = RESULT | {"is_error": True, "result": "failed"}
        answer = self._agent([MESSAGE, error])
        self.assertEqual(answer["error"], "agent_error")
        self.assertEqual(answer["detail"], "failed")
        self.assertEqual(answer["raw"], error)
        for payload in ([], [MESSAGE], [RESULT, RESULT],
                        ["private payload", RESULT]):
            with self.subTest(payload=payload):
                answer = self._agent(payload)
                self.assertEqual(answer["error"], "invalid_json")
                self.assertNotIn("private payload", answer["detail"])

    def test_canary_reads_array_and_reports_invalid_shape(self):
        self.assertEqual(self._canary([MESSAGE, RESULT]), {"reply": "done"})
        self.assertEqual(self._canary([RESULT, MESSAGE]), {"reply": "done"})
        error = self._canary([RESULT, RESULT])
        self.assertEqual(error["error"], "invalid_json")
        self.assertEqual(self._canary([MESSAGE, RESULT | {"is_error": True}])["error"],
                         "agent_error")

    def test_judge_reads_array_and_records_result_model_usage(self):
        text, models = self._judge([MESSAGE, RESULT])
        self.assertEqual(text, "done")
        self.assertEqual(models, [{"modelUsage": RESULT["modelUsage"]}])
        self.assertEqual(self._judge([RESULT, MESSAGE])[0], "done")
        with self.assertRaisesRegex(RuntimeError, "invalid JSON") as caught:
            self._judge(["private payload", RESULT])
        self.assertNotIn("private payload", str(caught.exception))

    def test_proposal_reads_array_and_refuses_invalid_shape(self):
        self.assertEqual(self._proposal([MESSAGE, RESULT]), "done")
        self.assertEqual(self._proposal([RESULT, MESSAGE]), "done")
        with self.assertRaises(propose_skill_edit.Refusal) as caught:
            self._proposal(["private payload", RESULT])
        self.assertNotIn("private payload", str(caught.exception))

    def test_raw_transcript_file_contains_only_normalized_result(self):
        raw = self._agent([MESSAGE, RESULT])["raw"]
        run_eval._write_summary(self.workspace, "fixture", "without_skill",
                                "20261004T000000Z", None, None, None, None, raw)
        saved = json.loads((self.workspace / "fixture" / "20261004T000000Z"
                            / "without_skill" / "transcripts" / "raw.json").read_text())
        self.assertEqual(saved, RESULT)


if __name__ == "__main__":
    unittest.main()
