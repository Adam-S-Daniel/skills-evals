#!/usr/bin/env python3
"""Fail when code, config or prose restates a rule value that disagrees with
docs/rules.json (generated from evals/*.yml by scripts/build_rules.py).

    check_rule_restatements.py --rules docs/rules.json --root DIR [--root DIR ...]
        [--exclude GLOB ...]

Two passes over every text file under each root:

  code/config  a rule's name (a YAML key, or a constant that used to hold it,
               `names` in rules.json) followed within a few characters by a
               number, as in `retire_confidence: 0.9`,
               `policy.get("objective_margin", 0.15)`, `x ?? 0.9` after the
               name, or `HIGH_STOP_MIN_WITHOUT = 0.90`, must equal one of
               that name's current values. A number set next to a retired
               name (`retired_names`) always fails.
  prose        a curated phrase table (PHRASES) maps a number written in a
               phrase, with a context word nearby on the same line, to the
               rules it may restate: "80% confidence" near keep or removal
               wording, "20 pairs" near cap wording, "15 points" near margin
               wording, "$10" near "one use", "8 weeks" near census, floor
               or re-check wording. A number that equals none of those
               rules' current values fails.

Each finding prints as `path:line: <rule> found <x>, current <y>`; exit 1
on any finding, 0 when clean, 2 on bad arguments. Matching is lexical
(regex), which suits these tokens: the checker reads numbers next to names,
not code structure.

Skipped: any `test`/`tests`, `vendor` or `.claude` (worktrees) directory, `results/`, `routine-results/`,
`node_modules/`, `.git/`, built bundles CI rebuilds from source
(`tool/index.html`, `explorer/dist/`, `dashboard/page/`), fixture seeds
(`evals/*/seed/`, copies of other repositories) and fixture rubrics
(`evals/*/fixture.yaml`), CSS, ADR bodies (`docs/decisions/`, the
history), the generated `docs/rules.md` and `docs/rules.json`, and the
rule sources themselves (each root's `evals/gate-policy.yml`,
`removal-policy.yml`, `hook-policy.yml`, `scope-policy.yml`,
`usage-unknown.yml` and `stakes.yml`; other `evals/*-policy.yml` files are
checked), plus `--exclude` globs
(matched against the path relative to its root).
"""

from __future__ import annotations

import argparse
import fnmatch
import json
import math
from pathlib import Path
import re
import sys

TEXT_SUFFIXES = {".py", ".js", ".mjs", ".cjs", ".ts", ".tsx", ".jsx", ".svelte", ".vue",
                 ".yml", ".yaml", ".json", ".md", ".sh", ".bash", ".txt", ".toml", ".rb",
                 ".html", ".css", ".ps1"}
SKIP_DIRS = {".git", "node_modules", "test", "tests", "results", "routine-results",
             "__pycache__", ".venv", "venv", "vendor", ".claude"}
SKIP_PATHS = ("tool/index.html", "explorer/dist/*", "dashboard/page/*", "evals/*/seed/*",
              # A fixture's scoring rubric ("cap at 3 if ...") is task data.
              "evals/*/fixture.yaml",
              "*.css", "scripts/check_rule_restatements.py", "docs/decisions/*", "docs/rules.md",
              "docs/rules.json", "evals/gate-policy.yml", "evals/removal-policy.yml",
              "evals/hook-policy.yml", "evals/scope-policy.yml", "evals/usage-unknown.yml",
              "evals/stakes.yml")
MAX_BYTES = 2_000_000
#: A numeric literal, not a format spec (`:.0%`, `:.2f`) or part of a word.
NUMBER = r"(-?(?:\d+(?:\.\d+)?|\.\d+))(?![\w%.-])"
#: What may sit between a rule's name and its number: quotes or a closing
#: bracket, then a colon, an equals sign, a comma, an opening parenthesis
#: (`max_runs_per_cell` (20)), `??`/`||`, `) or` (`.get("key") or 0.9`), or a
#: type annotation (`NAME: int = 3`), then optionally `timedelta(weeks=`.
GAP = (r"""["'`\]\s]{0,2}\s*"""
       r"""(?:\)\s*or\b|:\s*[A-Za-z_][\w\[\], |.]{0,30}?\s*=(?!=)|[:=,(]|\?\?|\|\|)"""
       r"""\s*(?:timedelta\(weeks=)?["'`]?\s*""")

#: The prose table. Each row: a regex whose group 1 is the number, how to
#: read it (`frac` keeps it, `pct` divides by 100), the context words that
#: tie it to rules (any of them on the same line within WINDOW characters)
#: and, per context, the rule ids it may restate. A phrase whose context
#: words match no row is not checked.
WINDOW = 120
PHRASES = [
    {
        "name": "confidence level",
        "regex": r"(\d{1,3}(?:\.\d+)?)\s?%\s+(?:confiden|level)|confiden\w*\s+(?:of\s+|at\s+)?(\d{1,3}(?:\.\d+)?)\s?%",
        "scale": "pct",
        "contexts": [
            (r"\bkeep|\bbenefit\b|\bhelps?\b", ["gate-policy.yml#*.benefit_confidence"]),
            (r"\bremov|\bretire|no[- ]benefit|\bharm", ["gate-policy.yml#*.retire_confidence"]),
        ],
    },
    {
        "name": "confidence level",
        # The same as a fraction: "0.85 confidence", "confidence of 0.9".
        "regex": r"(?<![\w.])(0?\.\d+)\s+confiden|confiden\w*\s+(?:level\s+)?(?:of\s+|at\s+)?(0?\.\d+)(?![\w.%])",
        "scale": "frac",
        "contexts": [
            (r"\bkeep|\bbenefit\b|\bhelps?\b", ["gate-policy.yml#*.benefit_confidence"]),
            (r"\bremov|\bretire|no[- ]benefit|\bharm", ["gate-policy.yml#*.retire_confidence"]),
        ],
    },
    {
        "name": "pair cap",
        # "the cap of 40", "a cap at 20", "capped at 40".
        "regex": r"\bcap(?:ped)?\s+(?:of|at|is)\s+(\d{1,4})\b(?!\s?%)",
        "scale": "frac",
        "window": 80,
        "contexts": [
            (r"\bpauses?\b|withdr[ae]w", ["gate-policy.yml#*.max_removal_pauses"]),
            (r"\bpairs?\b|\bcells?\b|paired runs|comparison runs",
             ["gate-policy.yml#*.max_runs_per_cell", "gate-policy.yml#*.max_runs_high_cell"]),
        ],
    },
    {
        "name": "pair count",
        "regex": r"(\d{1,4})\s+(?:paired\s+runs|pairs)\b|(\d{1,4})-pair\b",
        "scale": "frac",
        "contexts": [
            (r"\bcap\b|\bcapped\b|at most|up to|\bmax|neither test|no[- ]clear[- ]effect",
             ["gate-policy.yml#*.max_runs_per_cell",
                                                     "gate-policy.yml#*.max_runs_high_cell"]),
            (r"current rest|rest guard|beside the current", [
                "gate-policy.yml#guidance.rest_guard_min_pairs"]),
            (r"\bbroken\b|cannot-discriminate", ["gate-policy.yml#*.floor_min_runs"]),
        ],
    },
    {
        "name": "objective margin",
        # A number right beside "margin" (not CSS's `margin:`/`margin-top`):
        # "a margin of 0.15", "0.15 margin", "15-point margin".
        "regex": r"\bmargins?\b(?![-:])[^.\d\n]{0,15}?(?<![\w.])(0?\.\d+|\d{1,2}(?=[- ](?:percentage[- ])?points?\b))"
                 r"|(?<![\w.])(0?\.\d+|\d{1,2}(?=[- ](?:percentage[- ])?points?\b))[^.\d\n]{0,15}\bmargins?\b",
        "scale": "points",
        "contexts": [
            (r"objective|\bremov|\bbenefit|\bretire|\bkeep\b|\bgain\b|\bjudge",
             ["gate-policy.yml#*.objective_margin", "gate-policy.yml#*.judge_margin"]),
        ],
    },
    {
        "name": "value of one use",
        "regex": r"\$(\d+(?:\.\d+)?)",
        "scale": "frac",
        "contexts": [
            (r"\b(?:one|a|per|each)\s+use\b", ["removal-policy.yml#value_per_use_usd"]),
        ],
    },
    {
        "name": "weeks",
        "regex": r"(\d{1,2})\s*(?:ISO\s+)?weeks?\b|(\d{1,2})-week\b",
        "scale": "frac",
        "contexts": [
            (r"re-?check", ["gate-policy.yml#*.recheck_weeks", "gate-policy.yml#*.recheck_weeks_high"]),
            (r"\bunused\b|zero[- ]use|first (?:recorded )?use|no recorded use",
             ["removal-policy.yml#floor_weeks", "removal-policy.yml#first_use_weeks"]),
            (r"\bfloor\b.{0,40}\b(?:remov|unused|use)|\b(?:remov|unused)\w*\b.{0,40}\bfloor\b",
             ["removal-policy.yml#floor_weeks"]),
            (r"\bhook\b.*\bverdict|\boverrid", ["hook-policy.yml#window_weeks"]),
        ],
    },
]
#: Prose that states a rule that no longer exists, whatever its number.
RETIRED_PHRASES = [
    (re.compile(r"\b\d[\d,]*[- ](?:full[- ]listing[- ])?sessions?\b.{0,80}\bzero[- ]use"
                r"|\bzero[- ]use\b.{0,80}\b\d[\d,]*[- ](?:full[- ]listing[- ])?sessions?\b",
                re.I),
     "zero-use session minimum",
     "evals pause until a skill's first recorded use, with no session minimum"),
    (re.compile(r"\bHol" r"m\b"), "Holm correction",
     "the keep test splits its level over the subject's cells (Bonferroni)"),
]


def _matches(rule_glob: str, rules: dict) -> list[str]:
    return [k for k in rules if fnmatch.fnmatchcase(k, rule_glob)]


def _values_by_name(rules: dict) -> dict[str, list]:
    """{name: [(rule id, value), ...]} over every numeric rule."""
    out: dict[str, list] = {}
    for rule_id, rule in rules.items():
        value = rule["value"]
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            continue
        for name in rule.get("names") or []:
            out.setdefault(name, []).append((rule_id, value))
    return out


def _equal(a: float, b: float) -> bool:
    return math.isclose(a, b, rel_tol=1e-9, abs_tol=1e-9)


def _fmt(value) -> str:
    return f"{value:g}" if isinstance(value, float) else str(value)


def skipped(rel: str, excludes: list[str]) -> bool:
    parts = rel.split("/")
    if any(p in SKIP_DIRS for p in parts[:-1]):
        return True
    return any(fnmatch.fnmatchcase(rel, g) for g in (*SKIP_PATHS, *excludes))


def files(root: Path, excludes: list[str]):
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.is_symlink() or path.suffix.lower() not in TEXT_SUFFIXES:
            continue
        rel = path.relative_to(root).as_posix()
        if skipped(rel, excludes):
            continue
        try:
            if path.stat().st_size > MAX_BYTES:
                continue
            yield rel, path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue


def check_text(rel: str, text: str, doc: dict) -> list[str]:
    """Findings for one file's text against the rules document `doc`."""
    rules = doc["rules"]
    by_name = _values_by_name(rules)
    retired = doc.get("retired_names") or {}
    findings = []
    name_re = re.compile(r"(?<![A-Za-z0-9_])(" + "|".join(
        sorted(map(re.escape, {*by_name, *retired}), key=len, reverse=True))
        + r")(?![A-Za-z0-9_])" + GAP + NUMBER)
    phrases = [(row, re.compile(row["regex"], re.I)) for row in PHRASES]
    # A retired name may not be set at all, to a number or a mapping.
    retired_set = re.compile(r"(?<![A-Za-z0-9_.])(" + "|".join(map(re.escape, retired))
                             + r")\s*(?::[^=\n]{1,40})?=(?!=)") if retired else None
    for number, line in enumerate(text.split("\n"), 1):
        if retired_set is not None:
            for m in retired_set.finditer(line):
                findings.append(f"{rel}:{number}: {m.group(1)} is retired "
                                f"({retired[m.group(1)]}); it is set here")
        for m in name_re.finditer(line):
            name, found = m.group(1), float(m.group(2))
            if name in retired:
                if retired_set is None or not retired_set.search(line[m.start():m.end()]):
                    findings.append(f"{rel}:{number}: {name} is retired ({retired[name]}); "
                                    f"found {m.group(2)}")
                continue
            current = by_name[name]
            if not any(_equal(found, v) for _, v in current):
                ids = sorted({r for r, _ in current})
                values = sorted({_fmt(v) for _, v in current})
                findings.append(f"{rel}:{number}: {', '.join(ids)} found {m.group(2)}, "
                                f"current {' or '.join(values)}")
        for row, regex in phrases:
            for m in regex.finditer(line):
                raw = next(g for g in m.groups() if g is not None)
                width = row.get("window", WINDOW)
                window = line[max(0, m.start() - width):m.end() + width]
                ids = []
                for context, globs in row["contexts"]:
                    if re.search(context, window, re.I):
                        for g in globs:
                            ids += _matches(g, rules)
                if not ids:
                    continue
                found = float(raw)
                if row["scale"] == "pct":
                    found /= 100
                elif row["scale"] == "points" and found >= 1:
                    found /= 100
                values = {rules[i]["value"] for i in ids}
                if not any(_equal(found, v) for v in values
                           if isinstance(v, (int, float)) and not isinstance(v, bool)):
                    findings.append(
                        f"{rel}:{number}: {row['name']} ({', '.join(sorted(set(ids)))}) found "
                        f"{raw}, current {' or '.join(sorted(_fmt(v) for v in values))}")
        for regex, what, why in RETIRED_PHRASES:
            if regex.search(line):
                findings.append(f"{rel}:{number}: {what} is not a rule ({why})")
    return findings


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--rules", type=Path, required=True, help="docs/rules.json")
    parser.add_argument("--root", type=Path, action="append", required=True,
                        help="a tree to check (repeatable)")
    parser.add_argument("--exclude", action="append", default=[],
                        help="a glob of paths to skip, relative to its root (repeatable)")
    args = parser.parse_args(argv)
    try:
        doc = json.loads(args.rules.read_text(encoding="utf-8"))
        if not isinstance(doc, dict) or not isinstance(doc.get("rules"), dict):
            raise ValueError("no rules mapping")
    except (OSError, ValueError) as error:
        print(f"check_rule_restatements: cannot read {args.rules}: {error}", file=sys.stderr)
        return 2
    findings = []
    for root in args.root:
        if not root.is_dir():
            print(f"check_rule_restatements: {root} is not a directory", file=sys.stderr)
            return 2
        label = root.resolve().name
        for rel, text in files(root, args.exclude):
            findings += [f"{label}/{f}" for f in check_text(rel, text, doc)]
    for line in findings:
        print(line)
    if findings:
        print(f"{len(findings)} restatement(s) disagree with {args.rules}; link "
              "docs/rules.md instead of restating a number", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
