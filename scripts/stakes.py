#!/usr/bin/env python3
"""Load evals/stakes.yml: each skill's and guidance section's stakes level.

`load(path, evals_dir)` returns {("skill", name) | ("guidance", section):
{"stakes", "reason", "covered_by"}} for the rows the file has; a subject with
no row is `normal` (`level_of`). The file's header says what each level means
and what the planner does with it (scripts/plan_week.py, THE BANDS).

`--check` loads the committed file and exits 1 with one line per problem, so
a malformed row fails CI (test/issues/test_issue_stakes.py runs it too).
"""
from __future__ import annotations

import argparse
from pathlib import Path
import re
import sys

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_PATH = REPO_ROOT / "evals" / "stakes.yml"
LEVELS = ("high", "normal", "none")
FLEET_OWNERS = ("Adam-S-Daniel", "jodidaniel")
#: `<owner>/<repo>:<path>`, the owner one of the fleet's two.
COVERED_BY_RE = re.compile(r"(?:%s)/[A-Za-z0-9._-]+:[^\s:]+" % "|".join(FLEET_OWNERS))
NAME_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}")


class StakesError(ValueError):
    pass


def _row(row, kind: str, key: str, evals_dir: Path) -> tuple:
    where = f"stakes {kind} row"
    if not isinstance(row, dict):
        raise StakesError(f"{where}: not a mapping")
    allowed = {key, "stakes", "reason", "covered_by"}
    extra = set(row) - allowed
    if extra:
        raise StakesError(f"{where}: unknown field(s) {sorted(extra)}")
    name = row.get(key)
    if not isinstance(name, str) or not NAME_RE.fullmatch(name) or name.startswith("_"):
        raise StakesError(f"{where}: `{key}` must be a plain name")
    folder = evals_dir / "guidance" / name if kind == "guidance" else evals_dir / name
    if (kind == "skill" and name == "guidance") or not folder.is_dir():
        raise StakesError(f"{where} {name}: no fixture directory {folder.relative_to(evals_dir.parent)}")
    level = row.get("stakes")
    if level not in LEVELS:
        raise StakesError(f"{where} {name}: `stakes` must be one of {', '.join(LEVELS)}")
    reason = row.get("reason")
    if not isinstance(reason, str) or not reason.strip():
        raise StakesError(f"{where} {name}: `reason` is required")
    covered = row.get("covered_by")
    if level == "none":
        if not isinstance(covered, str) or not COVERED_BY_RE.fullmatch(covered):
            raise StakesError(f"{where} {name}: a `none` row needs `covered_by` as "
                              "<owner>/<repo>:<path>, the check that enforces it")
    elif covered is not None:
        raise StakesError(f"{where} {name}: only a `none` row names `covered_by`")
    return (kind, name), {"stakes": level, "reason": reason.strip(), "covered_by": covered}


def load(path: Path, evals_dir: Path) -> dict:
    """The rows of `path`, keyed by (kind, name). A missing file is empty."""
    if not path.is_file():
        return {}
    doc = yaml.safe_load(path.read_text(encoding="utf-8"))
    if doc is None:
        return {}
    if not isinstance(doc, dict) or set(doc) - {"skills", "sections"}:
        raise StakesError("stakes file: top level is `skills:` and `sections:` only")
    out: dict = {}
    for top, kind, key in (("skills", "skill", "skill"), ("sections", "guidance", "section")):
        rows = doc.get(top) or []
        if not isinstance(rows, list):
            raise StakesError(f"stakes file: `{top}` must be a list")
        for row in rows:
            subject, entry = _row(row, kind, key, evals_dir)
            if subject in out:
                raise StakesError(f"stakes {kind} row {subject[1]}: duplicate")
            out[subject] = entry
    return out


def level_of(table: dict, kind: str, name: str) -> str:
    entry = table.get((kind, name))
    return entry["stakes"] if entry else "normal"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--check", action="store_true", help="validate the file and exit")
    parser.add_argument("--path", type=Path, default=DEFAULT_PATH)
    args = parser.parse_args(argv)
    try:
        table = load(args.path, args.path.parent)
    except (StakesError, yaml.YAMLError) as exc:
        print(f"stakes: {exc}", file=sys.stderr)
        return 1
    counts = {level: sum(1 for e in table.values() if e["stakes"] == level) for level in LEVELS}
    print(f"stakes: ok ({counts['high']} high, {counts['none']} none, the rest normal)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
