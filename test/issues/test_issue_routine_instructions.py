"""The eval runner routine reads its instructions from the repo (Adam, 2026-11-03).

Every change to the routine used to need Adam to paste a new prompt by hand.
The routine's prompt is now a stub that reads
docs/routine/eval-runner-instructions.md at origin/main, so changes land as
pull requests. These tests keep the stub pointing at a file that exists, keep
it a stub, and keep every mode reachable from the file it points to.

An eval fire read the whole 31 KB file for the few lines it needed. Its steps
are now scripts/routine_eval.py, and each other mode's section is its own file
under docs/routine/modes/, which the main file names by path and tells the
routine to read from the same commit, in that mode only. So the main file stays
short, and these tests hold each mode file to its section.
"""
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PROMPT_DOC = ROOT / "docs" / "routine" / "eval-runner-prompt.md"
INSTRUCTIONS_REL = "docs/routine/eval-runner-instructions.md"
INSTRUCTIONS = ROOT / INSTRUCTIONS_REL
#: Each mode's file under docs/routine/modes/ and the heading it starts with.
MODES = {"scaffold": "SCAFFOLD MODE:\n", "improve": "IMPROVE MODE (",
         "guidance-improve": "GUIDANCE-IMPROVE MODE (", "draft": "DRAFT MODE ("}
MODES_REL = "docs/routine/modes"


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

    def test_every_mode_is_reachable_from_the_instructions_file(self):
        text = INSTRUCTIONS.read_text(encoding="utf-8")
        self.assertIn("EVAL STEPS:", text)
        self.assertRegex(text, r"Limits: .*\n")
        for mode, heading in MODES.items():
            with self.subTest(mode=mode):
                rel = f"{MODES_REL}/{mode}.md"
                self.assertIn(f"In {mode} mode only, read it with "
                              f"`git show <INSTRUCTIONS_SHA>:{rel}` (the same commit as this "
                              "file, never another ref) and follow it as part of these "
                              "instructions.", text)
                self.assertTrue((ROOT / rel).read_text(encoding="utf-8").startswith(heading))
                # The section moved out whole: its heading is no longer here.
                self.assertNotIn("\n" + heading, text)
        self.assertEqual(sorted(p.name for p in (ROOT / MODES_REL).iterdir()),
                         sorted(f"{mode}.md" for mode in MODES))

    def test_draft_mode_can_reach_the_improve_steps_it_cites(self):
        draft = (ROOT / MODES_REL / "draft.md").read_text(encoding="utf-8")
        self.assertIn("as IMPROVE MODE does", draft)
        self.assertIn('Where it says "as IMPROVE MODE does", read '
                      f"{MODES_REL}/improve.md the same way for that step.",
                      INSTRUCTIONS.read_text(encoding="utf-8"))
        improve = (ROOT / MODES_REL / "improve.md").read_text(encoding="utf-8")
        self.assertIn("g.refused_env_names(os.environ)", improve)
        self.assertIn("2a40fd2e7c52207aa903bd33fc4c65716126966e", improve)

    def test_the_eval_steps_are_the_script(self):
        text = INSTRUCTIONS.read_text(encoding="utf-8")
        steps = text[text.index("\nEVAL STEPS:"):text.index("\nSCAFFOLD MODE is ")]
        self.assertIn("`git checkout --quiet --detach <INSTRUCTIONS_SHA> && "
                      "python3 scripts/routine_eval.py --payload <that file>`", steps)
        # Two models' runs of 40 minutes each, plus setup and the push.
        self.assertIn("timeout of 5400000 ms (90 minutes;", steps)
        self.assertIn("Write the fire text, unchanged, to a new file outside every checkout",
                      steps)
        self.assertIn("do not run it again", steps)
        self.assertIn('"instructions: <INSTRUCTIONS_SHA>"', steps)
        self.assertTrue((ROOT / "scripts" / "routine_eval.py").is_file())

    def test_an_eval_fire_reads_a_short_file(self):
        # Every fire reads the whole main file; only the other modes read more.
        self.assertLess(len(INSTRUCTIONS.read_bytes()), 8000)

    def test_the_instructions_files_are_plain_text_not_wrapped_fences(self):
        # The routine follows each whole file, so each holds instructions only.
        text = INSTRUCTIONS.read_text(encoding="utf-8")
        self.assertTrue(text.startswith("You are the skills-evals EVAL RUNNER routine"))
        for path in (INSTRUCTIONS, *sorted((ROOT / MODES_REL).iterdir())):
            with self.subTest(path=path.name):
                self.assertNotIn("```text", path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
