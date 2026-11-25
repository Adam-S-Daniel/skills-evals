"""Every tracked file is clear of the owner's private denylist.

The fleet's agent-checks privacy check (.githooks/privacy-denylist.py, which
_agent-guidance syncs here) reads ref names, commit messages and identities
on a push; nothing read file CONTENT, so names built on a private detail sat
in this repo's code until a downstream copy's leak scan caught them. This
test scans the whole tree: every tracked file's path and text, case-
insensitively, with no allowance and no excluded path.

The patterns are never in this repository. They come from PRIVACY_DENYLIST
(newline-separated regular expressions; ci.yml passes the repository secret)
or the file PRIVACY_DENYLIST_FILE names, parsed by the fleet checker's own
loader, so the format is the fleet's: one pattern per line, `#` comments,
matched case-insensitively. The checker's ~/.config default is not read: a
local run scans only when one of the two variables is set.

A hit is reported as `path:line: pattern #N` (`<file #K>` in place of a path
that itself matches), never the matched text or the pattern, so a CI log
never repeats what it protects. With no denylist the scan FAILS in CI (a
green scan that checked nothing is worse than a red one) and is skipped
locally, where a contributor may not hold the list.

Run: python3 -m pytest test/issues/test_issue_privacy_denylist_scan.py -q
"""

from __future__ import annotations

import importlib.util
import os
import re
import subprocess
import sys
import tempfile
import unittest
import unittest.mock
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "test"))
from prereqs import in_ci  # noqa: E402

_spec = importlib.util.spec_from_file_location(
    "fleet_privacy_denylist", ROOT / ".githooks" / "privacy-denylist.py")
fleet = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(fleet)

SOURCES = (fleet.ENV_PATTERNS, fleet.ENV_FILE)


def load_denylist(environ) -> list | None:
    """The compiled patterns from PRIVACY_DENYLIST or PRIVACY_DENYLIST_FILE,
    or None when neither is set. Only those two variables reach the fleet
    loader, so its home-directory default is never read."""
    return fleet.load_patterns({k: environ[k] for k in SOURCES if environ.get(k)})


def tracked_files(root: Path) -> list[tuple[str, str]]:
    """(path, text) for every tracked file; a file holding a NUL byte is
    binary and contributes its path only."""
    listed = subprocess.run(["git", "-C", str(root), "ls-files", "-z"],
                            check=True, capture_output=True).stdout
    out = []
    for rel in sorted(p for p in listed.decode("utf-8").split("\0") if p):
        path = root / rel
        data = path.read_bytes() if path.is_file() else b""
        out.append((rel, "" if b"\0" in data else data.decode("utf-8", errors="replace")))
    return out


def denylist_hits(patterns, files) -> list[str]:
    """`path:line: pattern #N` for every hit, never the text or the pattern."""
    out = []
    for position, (rel, text) in enumerate(files, start=1):
        path_hits = [i for i, p in enumerate(patterns, start=1) if p.search(rel)]
        label = f"<file #{position}>" if path_hits else rel
        out += [f"{label}:path: pattern #{i}" for i in path_hits]
        for i, p in enumerate(patterns, start=1):
            if not p.search(text):
                continue
            out += [f"{label}:{number}: pattern #{i}"
                    for number, line in enumerate(text.splitlines(), start=1) if p.search(line)]
    return out


class TreeHoldsNothingFromTheDenylist(unittest.TestCase):
    def test_every_tracked_file_is_clear_of_the_private_denylist(self):
        try:
            patterns = load_denylist(os.environ)
        except fleet.CheckError as exc:
            self.fail(f"privacy denylist: {exc}")
        if patterns is None:
            if in_ci():
                self.fail(f"no privacy denylist in CI: set {fleet.ENV_PATTERNS} from the "
                          "repository secret (ci.yml's Run tests step passes it)")
            raise unittest.SkipTest(f"no privacy denylist ({fleet.ENV_PATTERNS} or "
                                    f"{fleet.ENV_FILE}); the tree scan did not run")
        hits = denylist_hits(patterns, tracked_files(ROOT))
        self.assertEqual(hits, [], "privacy denylist matched:\n  " + "\n  ".join(hits))


class Scanner(unittest.TestCase):
    """The scanner itself, against an invented stand-in name."""

    NAME = "zephyr" + "box"  # invented; assembled so no line holds it whole

    def patterns(self):
        return load_denylist({fleet.ENV_PATTERNS: f"# a comment\n\n{self.NAME}\n"})

    def test_finds_the_name_in_any_case_and_inside_identifiers(self):
        n, cap, up = self.NAME, self.NAME.capitalize(), self.NAME.upper()
        lines = ["clean line", n, cap, up, f"def scan_{n}_tasks():", f"run{cap}Tasks()",
                 f"--{n}-tasks", f"class {cap}Tasks:", "clean again"]
        hits = denylist_hits(self.patterns(), [("src/a.py", "\n".join(lines) + "\n")])
        self.assertEqual(hits, [f"src/a.py:{k}: pattern #1" for k in range(2, 9)])

    def test_a_file_name_hit_hides_the_path_and_no_output_holds_the_name(self):
        files = [("docs/clean.md", "nothing\n"),
                 (f"scripts/scan_{self.NAME.upper()}.sh", f"echo {self.NAME}\n")]
        hits = denylist_hits(self.patterns(), files)
        self.assertEqual(hits, ["<file #2>:path: pattern #1", "<file #2>:1: pattern #1"])
        self.assertTrue(all(self.NAME not in h.lower() for h in hits))

    def test_pattern_numbers_skip_comments_and_blank_lines(self):
        patterns = load_denylist({fleet.ENV_PATTERNS: f"# c\nnomatch\n\n{self.NAME}\n"})
        self.assertEqual(denylist_hits(patterns, [("a.txt", self.NAME)]), ["a.txt:1: pattern #2"])

    def test_scans_tracked_files_including_binary_paths(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            subprocess.run(["git", "init", "-q", str(root)], check=True)
            (root / "a.txt").write_text(f"x\n{self.NAME.capitalize()}\n", encoding="utf-8")
            (root / f"{self.NAME}.bin").write_bytes(b"\0" + self.NAME.encode())
            (root / "untracked.txt").write_text(self.NAME, encoding="utf-8")
            subprocess.run(["git", "-C", str(root), "add", "a.txt", f"{self.NAME}.bin"], check=True)
            hits = denylist_hits(self.patterns(), tracked_files(root))
        self.assertEqual(hits, ["a.txt:2: pattern #1", "<file #2>:path: pattern #1"])

    def test_loader_reads_only_the_two_variables_and_names_no_pattern(self):
        self.assertIsNone(load_denylist({}))
        self.assertIsNone(load_denylist({"HOME": "/nonexistent-home"}))
        self.assertIsNone(load_denylist({fleet.ENV_PATTERNS: "  \n# only a comment\n"}))
        with tempfile.TemporaryDirectory() as tmp:
            listing = Path(tmp) / "list.txt"
            listing.write_text(f"{self.NAME}\n", encoding="utf-8")
            self.assertEqual([p.pattern for p in load_denylist({fleet.ENV_FILE: str(listing)})],
                             [self.NAME])
        with self.assertRaises(fleet.CheckError) as err:
            load_denylist({fleet.ENV_PATTERNS: "fine\n(unclosed"})
        self.assertIn("pattern #2 ", str(err.exception))
        self.assertNotIn("unclosed", str(err.exception))

    def test_ci_without_a_denylist_fails_instead_of_skipping(self):
        env = {k: v for k, v in os.environ.items() if k not in SOURCES}
        env["CI"] = "true"
        case = TreeHoldsNothingFromTheDenylist("test_every_tracked_file_is_clear_of_the_private_denylist")
        with unittest.mock.patch.dict(os.environ, env, clear=True):
            with self.assertRaisesRegex(AssertionError, "no privacy denylist in CI"):
                case.test_every_tracked_file_is_clear_of_the_private_denylist()
            env["CI"] = "false"
            with unittest.mock.patch.dict(os.environ, env, clear=True):
                with self.assertRaises(unittest.SkipTest):
                    case.test_every_tracked_file_is_clear_of_the_private_denylist()


if __name__ == "__main__":
    unittest.main()
