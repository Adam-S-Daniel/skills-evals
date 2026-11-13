#!/usr/bin/env python3
"""Re-pin in-place fixtures whose context drifted and whose evidence is free.

`scripts/explorer_data.py` raises `context-drift` (#545) for a scheduled
in-place skill fixture whose sibling skills moved on its context repository's
main more than CONTEXT_DRIFT_DAYS ago. The fix is a re-pin: point
`context.revision` and `context.guidance_revision` at the repository's
current HEAD. A re-pin changes the fixture's `fixture_digest`, so every
ingested run at the old pin stops pooling. Owner policy (2026-11-13): a pin
holds while its evidence is in use; it is re-pinned automatically only when
the evidence would restart anyway (`explorer_data.drift_evidence`). This
step touches only those fixtures: HEALTH FILTER fixtures in `alert` state
whose evidence is `free`.

For each, it measures the context at the repository's checked-out HEAD, as a
run does (`contextualize_fixtures.Measurer`; the repository never changes).
The committed `context.budget` stays as it is: the fixture is re-pinned only
when the larger arm's bytes fit every committed key. One that does not fit is
listed as `over_budget` and left alone, for a person or agent to raise the
budget (ADR 0012, "Context budgets") before re-pinning.

The rewrite changes the two `revision` lines inside the top-level `context:`
block and sets one comment line directly above it (an earlier re-pin comment
is replaced, never stacked). The file is parsed before and after, and any
other difference raises.

    python3 scripts/repin_drifted_fixtures.py \\
        --context-repo OWNER/REPO=PATH ... --registry NAME=PATH ... \\
        --results-tree DIR --as-of TIME [--apply]

stdout is `count=N`, `fixtures=<paths>` and `over_budget=<paths>`, for
$GITHUB_OUTPUT.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "harness"))
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import yaml  # noqa: E402

import context  # noqa: E402
import contextualize_fixtures as cf  # noqa: E402
import explorer_data  # noqa: E402
import run_eval  # noqa: E402
import scaffold_real_work as scaffold  # noqa: E402
import stakes as stakes_mod  # noqa: E402

COMMENT_PREFIX = "# Re-pinned on "
COMMENT_SUFFIX = " by scripts/repin_drifted_fixtures.py (context drift, evidence not in use)."


def comment(date: str) -> str:
    return f"{COMMENT_PREFIX}{date}{COMMENT_SUFFIX}"


def fits(measured: dict, committed: dict) -> bool:
    """Whether each key's larger-arm bytes are within the committed budget."""
    return all(isinstance(committed.get(key), int) and measured[key] <= committed[key]
               for key in context.BUDGET_KEYS)


def render_repin(target: Path, metadata: dict, date: str) -> str:
    """`target`'s text with `revision` and `guidance_revision` in the
    top-level `context:` block rewritten and the re-pin comment set above it;
    raise on any other change. Writes nothing."""
    text = target.read_text(encoding="utf-8")
    before = yaml.safe_load(text)
    lines = text.split("\n")
    starts = [i for i, line in enumerate(lines) if line == "context:"]
    if not isinstance(before, dict) or not isinstance(before.get("context"), dict) \
            or len(starts) != 1:
        raise scaffold.ScaffoldError(f"{target}: not one top-level `context:` block")
    start = starts[0]
    end = start + 1
    while end < len(lines) and (lines[end].startswith(" ") or lines[end] == ""):
        end += 1
    for key in ("revision", "guidance_revision"):
        found = [i for i in range(start + 1, end) if re.fullmatch(rf"  {key}: \S+", lines[i])]
        if len(found) != 1:
            raise scaffold.ScaffoldError(f"{target}: not one `{key}` line in `context:`")
        lines[found[0]] = f"  {key}: {metadata[key]}"
    if start > 0 and lines[start - 1].startswith(COMMENT_PREFIX) \
            and lines[start - 1].endswith(COMMENT_SUFFIX):
        lines[start - 1] = comment(date)
    else:
        lines.insert(start, comment(date))
    after_text = "\n".join(lines)
    expected = {**before, "context": {**before["context"],
                                      "revision": metadata["revision"],
                                      "guidance_revision": metadata["guidance_revision"]}}
    if yaml.safe_load(after_text) != expected:
        raise scaffold.ScaffoldError(f"{target}: re-pinning changed something else")
    return after_text


def write_repin(target: Path, metadata: dict, date: str) -> None:
    target.write_text(render_repin(target, metadata, date), encoding="utf-8")


def repin(root: Path, measure, alerting: list, date: str, apply: bool) -> tuple:
    """(done, over_budget, skipped) over `alerting`, the free alerting HEALTH
    FILTER entries: done is [(path, metadata)], over_budget [path], skipped
    [(path, reason)]. With `apply`, the done fixtures are written."""
    done, over, skipped = [], [], []
    for entry in alerting:
        path = entry["fixture"]
        try:
            metadata = measure(root / path, entry["context"]["repository"])
        except (cf.Skip, scaffold.ScaffoldError, subprocess.CalledProcessError, OSError,
                ValueError) as why:
            skipped.append((path, str(why)))
            continue
        if fits(metadata["measured"], entry["context"].get("budget") or {}):
            done.append((path, metadata))
        else:
            over.append(path)
    if apply:
        # Every text is rendered (and checked) before any is written, so a
        # refusal leaves the tree as it was.
        texts = [(root / path / cf.FIXTURE_FILE,
                  render_repin(root / path / cf.FIXTURE_FILE, metadata, date))
                 for path, metadata in done]
        for target, text in texts:
            target.write_text(text, encoding="utf-8")
    return done, over, skipped


def alerting_free(root: Path, results_tree: Path, repositories: dict, now, compact: str) -> list:
    """The HEALTH FILTER entries in `alert` state whose evidence is free."""
    evals_dir = root / "evals"
    index = explorer_data.compute_gates.build_index(results_tree, evals_dir, compact)
    table = stakes_mod.load(evals_dir / "stakes.yml", evals_dir)
    names = set(explorer_data.public_census(explorer_data.load_census(results_tree))[0])
    _alerts, _unknown, rows, _held = explorer_data.health_alerts(
        evals_dir, names, repositories, now, index["runs"],
        explorer_data.open_batch_skills(results_tree),
        lambda skill: stakes_mod.level_of(table, "skill", skill))
    free = {r["fixture"] for r in rows if r["evidence"] == "free"}
    return [e for e in explorer_data.health_fixtures(evals_dir, names) if e["fixture"] in free]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    parser.add_argument("--context-repo", action="append", default=[],
                        metavar="OWNER/REPO=PATH")
    parser.add_argument("--registry", action="append", default=[], metavar="NAME=PATH")
    parser.add_argument("--results-tree", required=True, type=Path)
    parser.add_argument("--as-of", required=True)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args(argv)
    try:
        as_of = explorer_data.compute_gates.parse_as_of(args.as_of)
        now = explorer_data.plan_week._stamp_time(as_of)
        repositories = context.parse_context_repos(args.context_repo)
        registries = run_eval.resolve_registries(args.registry, None, REPO_ROOT)
        alerting = alerting_free(REPO_ROOT, args.results_tree, repositories, now, as_of)
    except (ValueError, OSError, context.ContextError, explorer_data.plan_week.PlanError) as error:
        print(f"repin_drifted_fixtures: bad arguments ({type(error).__name__})", file=sys.stderr)
        return 2
    date = f"{as_of[:4]}-{as_of[4:6]}-{as_of[6:8]}"
    try:
        done, over, skipped = repin(REPO_ROOT, cf.Measurer(repositories, registries),
                                    alerting, date, args.apply)
    except scaffold.ScaffoldError as error:
        print(f"repin_drifted_fixtures: {error}", file=sys.stderr)
        return 2
    for path, reason in skipped:
        print(f"skipped {path}: {reason}", file=sys.stderr)
    for path in over:
        print(f"over budget {path}: the re-measured larger arm exceeds the committed budget",
              file=sys.stderr)
    for path, metadata in done:
        print(f"{path}: {metadata['repository']}@{metadata['revision'][:12]}", file=sys.stderr)
    print(f"count={len(done)}")
    print("fixtures=" + " ".join(path for path, _ in done))
    print("over_budget=" + " ".join(over))
    return 0


if __name__ == "__main__":
    sys.exit(main())
