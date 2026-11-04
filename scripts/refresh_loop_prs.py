#!/usr/bin/env python3
"""Bring a conflicted loop pull request up to date with its base (#623).

  refresh_loop_prs.py merge --repo DIR --base REF

Every loop pull request (adam-agentskills `draft-skill/`, `eval-improve/`,
`retire-skill/`; skills-evals `draft-skill-fixtures/`) adds its record to
the same append-only places: `docs/skill-impact.md` (an entry under the
log's `---`), `scripts/plugin_layout.json` (a skill in a sorted list),
skills-evals' `README.md` layout block and `evals/unscheduled.yml`. Two
such pull requests open at once always conflict there, and nothing else
would ever bring the second one up to date.

`merge` runs in a checkout whose HEAD is the pull request's head: it merges
REF (the base branch) in, and resolves each conflicted path that has a
resolver here by taking REF's version and re-applying what the pull
request itself added. Any other conflict, or an addition that is not one
contiguous block, aborts the merge and exits 3, leaving the branch as it
was for a person. Nothing from the branch is ever run: git merges data,
and the resolvers parse text and JSON.

Exit codes: 0 merged (or already up to date; `outcome=` says which), 3 a
conflict this cannot resolve, 2 a usage or git error.

  refresh_loop_prs.py removal-check --gates FILE --head REF

A removal pull request (`retire-skill/`, `retire-guidance/`) is refreshed
only while its subject's verdict in FILE (compute_gates.py's output) still
supports an automatic removal and the mode is `auto`
(retire_skill.refresh_allowed; ADR 0014, PR #724 round 1's M2): bringing a
stale one up to date would re-run its checks and let auto-merge fire before
the withdrawal reaches it. Exit 0 when the head may be refreshed (any other
head always may), 4 when it may not, with `reason=` naming why. A missing
or unreadable FILE is unknown data, so no removal is refreshed.
"""
from __future__ import annotations

import argparse
import difflib
import json
import subprocess
import sys
from pathlib import Path


class Unresolvable(Exception):
    pass


def added_block(base: str, head: str) -> str:
    """The lines `head` inserted into `base`, which must be one contiguous
    insertion and nothing else (no deletions or replacements)."""
    a, b = base.splitlines(keepends=True), head.splitlines(keepends=True)
    ops = [op for op in difflib.SequenceMatcher(None, a, b, autojunk=False).get_opcodes()
           if op[0] != "equal"]
    if len(ops) != 1 or ops[0][0] != "insert":
        raise Unresolvable("the pull request's change is not one inserted block")
    _, _, _, j1, j2 = ops[0]
    return "".join(b[j1:j2])


def _insert_after(text: str, anchor: str, block: str, what: str,
                  before: str = "") -> str:
    """`block` right after the first `anchor`, or, with `before`, right
    after the first `anchor` that is followed by `before` (a line anchor:
    `anchor="\\n", before="  real-work/"` is the start of that line)."""
    i = text.find(anchor + before)
    if i < 0:
        raise Unresolvable(f"{what}: the base has no anchor {(anchor + before)!r}")
    i += len(anchor)
    return text[:i] + block + text[i:]


def _check_new(main: str, block: str, what: str) -> None:
    if not block.strip():
        raise Unresolvable(f"{what}: the pull request added nothing")
    if block in main:
        raise Unresolvable(f"{what}: the base already has the pull request's block")


def resolve_skill_impact(base: str, main: str, head: str) -> str:
    """The log is newest first: the pull request's entry goes right under
    the `---` that ends the header, above every entry the base gained."""
    block = added_block(base, head)
    _check_new(main, block, "docs/skill-impact.md")
    return _insert_after(main, "\n---\n\n", block, "docs/skill-impact.md")


def resolve_unscheduled(base: str, main: str, head: str) -> str:
    """Rows are appended at the end of the file."""
    block = added_block(base, head)
    _check_new(main, block, "evals/unscheduled.yml")
    if not block.startswith("  - path: evals/"):
        raise Unresolvable("evals/unscheduled.yml: the added block is not rows")
    return main + ("" if main.endswith("\n") else "\n") + block


def resolve_readme(base: str, main: str, head: str) -> str:
    """skills-evals' layout block: a drafted eval directory's lines go just
    above `real-work/`, as draft_new_skill.py `fixtures-apply` puts them."""
    block = added_block(base, head)
    _check_new(main, block, "README.md")
    if not block.startswith("  ") or "\n  real-work/" not in head:
        raise Unresolvable("README.md: the added block is not a layout entry")
    return _insert_after(main, "\n", block, "README.md", before="  real-work/")


def _layout(text: str) -> dict:
    doc = json.loads(text)
    plugins = doc.get("plugins") if isinstance(doc, dict) else None
    if set(doc) != {"plugins"} or not isinstance(plugins, dict) or not all(
            isinstance(e, dict) and isinstance(e.get("skills"), list) for e in plugins.values()):
        raise Unresolvable("scripts/plugin_layout.json: not the layout shape")
    return doc


def resolve_plugin_layout(base: str, main: str, head: str) -> str:
    """The base's layout plus the skills the pull request added and minus
    the ones it removed, in the file's one canonical form (adam-agentskills'
    test_the_layout_file_is_in_canonical_form)."""
    b, m, h = _layout(base), _layout(main), _layout(head)
    out = m
    for name in set(b["plugins"]) | set(h["plugins"]):
        before = set(b["plugins"].get(name, {}).get("skills", []))
        after = set(h["plugins"].get(name, {}).get("skills", []))
        if before == after:
            continue
        if name not in out["plugins"]:
            raise Unresolvable("scripts/plugin_layout.json: the pull request changes a "
                               "plugin the base does not have")
        skills = (set(out["plugins"][name]["skills"]) | (after - before)) - (before - after)
        out["plugins"][name]["skills"] = sorted(skills)
    out["plugins"] = {k: out["plugins"][k] for k in sorted(out["plugins"])}
    return json.dumps(out, indent=2) + "\n"


RESOLVERS = {
    "docs/skill-impact.md": resolve_skill_impact,
    "evals/unscheduled.yml": resolve_unscheduled,
    "README.md": resolve_readme,
    "scripts/plugin_layout.json": resolve_plugin_layout,
}


def git(repo: Path, *args: str, check: bool = True) -> str:
    done = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True)
    if check and done.returncode != 0:
        raise RuntimeError(f"git {args[0]} failed ({done.returncode})")
    return done.stdout


def show(repo: Path, rev: str, path: str) -> str:
    return git(repo, "show", f"{rev}:{path}")


def merge(repo: Path, base: str) -> str:
    """Merge `base` into HEAD and resolve what RESOLVERS cover. Returns
    `up-to-date` or `merged`; raises Unresolvable after aborting."""
    head = git(repo, "rev-parse", "HEAD").strip()
    if subprocess.run(["git", "-C", str(repo), "merge-base", "--is-ancestor", base, head],
                      capture_output=True).returncode == 0:
        return "up-to-date"
    fork = git(repo, "merge-base", base, head).strip()
    done = subprocess.run(["git", "-C", str(repo), "merge", "--no-ff", "--no-commit", base],
                          capture_output=True, text=True)
    conflicted = [p for p in git(repo, "diff", "--name-only", "--diff-filter=U").splitlines() if p]
    if done.returncode != 0 and not conflicted:
        git(repo, "merge", "--abort", check=False)
        raise RuntimeError("git merge failed without a conflict")
    try:
        for path in conflicted:
            resolver = RESOLVERS.get(path)
            if resolver is None:
                raise Unresolvable(f"{path}: no resolver for this path")
            try:
                text = resolver(show(repo, fork, path), show(repo, base, path),
                                show(repo, head, path))
            except (ValueError, RuntimeError) as exc:
                raise Unresolvable(f"{path}: {exc}") from None
            (repo / path).write_text(text, encoding="utf-8")
            git(repo, "add", "--", path)
    except Unresolvable:
        git(repo, "merge", "--abort", check=False)
        raise
    names = ", ".join(conflicted) or "none"
    git(repo, "-c", "user.name=skills-evals loop refresh",
        "-c", "user.email=skills-evals@users.noreply.github.com",
        "commit", "-q", "-m",
        f"Merge {base} into this loop pull request\n\n"
        f"Re-resolved the append-only paths both sides added to: {names} "
        "(scripts/refresh_loop_prs.py, skills-evals#623).")
    return "merged"


def removal_check(gates_path: Path, head: str) -> int:
    """`removal-check`: 0 when `head` may be refreshed, 4 when it may not.
    retire_skill is imported here, not at the top, so `merge` keeps needing
    nothing beyond the standard library."""
    import retire_skill
    try:
        gates = retire_skill.load_gates(gates_path)
    except retire_skill.RetireError:
        gates = None
    ok, why = retire_skill.refresh_allowed(gates, head)
    print(f"outcome={'refresh' if ok else 'skip'}\nreason={why}")
    return 0 if ok else 4


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    sub = parser.add_subparsers(dest="command", required=True)
    m = sub.add_parser("merge")
    m.add_argument("--repo", type=Path, required=True)
    m.add_argument("--base", required=True)
    c = sub.add_parser("removal-check")
    c.add_argument("--gates", type=Path, required=True)
    c.add_argument("--head", required=True)
    args = parser.parse_args(argv)
    if args.command == "removal-check":
        return removal_check(args.gates, args.head)
    try:
        outcome = merge(args.repo, args.base)
    except Unresolvable as exc:
        print(f"outcome=unresolvable\nreason={exc}")
        return 3
    except RuntimeError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print(f"outcome={outcome}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
