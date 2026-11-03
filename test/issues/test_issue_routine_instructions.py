"""The eval runner routine reads its instructions from the repo (Adam, 2026-11-03).

Every change to the routine used to need Adam to paste a new prompt by hand.
The routine's prompt is now a stub that reads
docs/routine/eval-runner-instructions.md at origin/main, so changes land as
pull requests. These tests keep the stub pointing at a file that exists, keep
it a stub, and keep every mode in the file it points to.
"""
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PROMPT_DOC = ROOT / "docs" / "routine" / "eval-runner-prompt.md"
INSTRUCTIONS_REL = "docs/routine/eval-runner-instructions.md"
INSTRUCTIONS = ROOT / INSTRUCTIONS_REL


def stub() -> str:
    text = PROMPT_DOC.read_text(encoding="utf-8")
    fences = re.findall(r"^```text\n(.*?)\n```$", text, re.S | re.M)
    assert len(fences) == 1, f"expected one text fence, found {len(fences)}"
    return fences[0]


class StubTests(unittest.TestCase):

    def test_the_stub_reads_the_instructions_file_from_origin_main(self):
        self.assertIn(f"git show origin/main:{INSTRUCTIONS_REL}", stub())
        self.assertTrue(INSTRUCTIONS.is_file())

    def test_the_stub_treats_the_fire_text_as_data(self):
        self.assertIn("UNTRUSTED DATA", stub())

    def test_the_stub_fails_closed_without_the_file(self):
        self.assertIn("push nothing", stub())
        self.assertIn("RESULT: error (instructions unavailable)", stub())

    def test_the_stub_stays_a_stub(self):
        # The instructions belong in the file; a long stub means they crept back.
        self.assertLess(len(stub()), 2000)
        for heading in ("EVAL STEPS:", "IMPROVE MODE", "DRAFT MODE"):
            self.assertNotIn(heading, stub())


class InstructionsTests(unittest.TestCase):

    def test_every_mode_is_in_the_instructions_file(self):
        text = INSTRUCTIONS.read_text(encoding="utf-8")
        for heading in ("EVAL STEPS:", "SCAFFOLD MODE:", "IMPROVE MODE (",
                        "GUIDANCE-IMPROVE MODE (", "DRAFT MODE ("):
            self.assertIn(heading, text)
        self.assertRegex(text, r"Limits: .*\n")

    def test_the_instructions_file_is_plain_text_not_a_wrapped_fence(self):
        # The routine follows the whole file, so it holds the instructions only.
        text = INSTRUCTIONS.read_text(encoding="utf-8")
        self.assertTrue(text.startswith("You are the skills-evals EVAL RUNNER routine"))
        self.assertNotIn("```text", text)


if __name__ == "__main__":
    unittest.main()
