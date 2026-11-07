#!/usr/bin/env python3
"""agent_made.py — which git hook checks, skills and guidance sections agents
made, and what they did since (the explorer document's `agent_made`).

The fleet guidance's "Turn lessons into checks, skills and guidance" section
(_agent-guidance#451, 2026-11-04) tells every agent to capture a lesson that
could recur as a check first, else a skill, else a guidance section, and to
name each in a commit trailer, `Captures: check|skill|section <id>`. This
module answers the owner's question that came with it: which of those did
agents make, how many, and what did they do.

For every subject the explorer document already lists (`hooks.checks` whose
`where` is `fleet`, `skills`, `guidance.sections`) it finds the commit that
created it, read from local full-history checkouts with `git log`, no network:

  * a `Captures:` trailer naming the subject, when one exists (authoritative);
  * else the oldest commit that added it: a skill's `SKILL.md`
    (`--diff-filter=A`), a section's `## <heading>` line in its file, a check
    id's first appearance under `templates/agent-checks/` (`git log -S`).

A section that was renamed dates from its rename; a skill carried over when
the registry restarted (ADR 0013) dates from the restart. Both are noted as
the method's known floor, never guessed past.

The commit's `origin` is `agent` (author Claude, Claude Code or Codex, or an
`Agent:` / `Co-Authored-By: Claude|Codex` trailer), `loop` (a `[bot]` author:
the eval loops' Apps), or `person`. `under_rule` is true when the commit is no
older than the rule: the older of the first commit carrying the section
heading above and the first carrying its predecessor, the routing sentence
"becomes a check first" in "Finding your unknowns" (2026-10-26).

Impact is copied from the same document, never recomputed: a check's 8-week
`window_totals` (runs, blocks) and verdict, a skill's `usage.invocations` and
verdict, a section's verdict and runs on its current text.

Nothing personal leaves this module: no author names, emails or commit
messages, only a short sha, a date, an origin class and the subject's id. A
checkout that is missing or shallow gives `origin: null` (unknown), never a
guess.
"""
from __future__ import annotations

import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path

RULE_HEADING = "## Turn lessons into checks, skills and guidance"
RULE_FALLBACK = "becomes a check first"
BASE_MD = "agents-md/base.md"
CHECKS_DIR = "templates/agent-checks"
KINDS = ("check", "skill", "section")

_AGENT_AUTHORS = frozenset({"claude", "claude code", "codex"})
_AGENT_EMAILS = frozenset({"noreply@anthropic.com"})
_AGENT_TRAILER = re.compile(r"^(agent:\s*\S|co-authored-by:\s*(claude|codex)\b)", re.I | re.M)
_CAPTURES = re.compile(r"^Captures:\s*(check|skill|section)\s+([A-Za-z0-9][A-Za-z0-9._-]*)\s*$", re.M)
_SEP_FIELD, _SEP_REC = "\x1f", "\x1e"
_FORMAT = f"%H{_SEP_FIELD}%an{_SEP_FIELD}%ae{_SEP_FIELD}%cI{_SEP_FIELD}%B{_SEP_REC}"


def _git(repo: Path, *args: str) -> str | None:
    try:
        out = subprocess.run(["git", "-C", str(repo), *args], capture_output=True,
                             text=True, check=True, timeout=120)
    except (OSError, subprocess.SubprocessError):
        return None
    return out.stdout


def _commits(text: str | None) -> list[dict]:
    """`git log --format=_FORMAT` output as records, oldest last as git gives them."""
    if not text:
        return []
    out = []
    for rec in text.split(_SEP_REC):
        rec = rec.lstrip("\n")
        if not rec:
            continue
        parts = rec.split(_SEP_FIELD, 4)
        if len(parts) != 5:
            continue
        sha, name, email, date, body = parts
        out.append({"sha": sha, "name": name, "email": email, "date": _utc(date), "body": body})
    return out


def _utc(iso: str) -> str:
    """A git `%cI` date as UTC `YYYY-MM-DDTHH:MM:SSZ`, so dates compare as text."""
    return datetime.fromisoformat(iso.strip()).astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def origin(commit: dict) -> str:
    """`agent`, `loop` or `person` for one commit record."""
    name = commit["name"].strip().lower()
    if name in _AGENT_AUTHORS or commit["email"].strip().lower() in _AGENT_EMAILS \
            or _AGENT_TRAILER.search(commit["body"]):
        return "agent"
    if name.endswith("[bot]"):
        return "loop"
    return "person"


def usable(repo: Path | None) -> bool:
    """A full-history git checkout: a shallow one would date everything to its cut."""
    if repo is None or not Path(repo).is_dir():
        return False
    return (_git(repo, "rev-parse", "--is-shallow-repository") or "").strip() == "false"


def captures(repo: Path) -> dict:
    """{(kind, id): oldest commit record} for every `Captures:` trailer in the repo."""
    found: dict = {}
    for c in _commits(_git(repo, "log", "--no-merges", f"--format={_FORMAT}")):
        for kind, ident in _CAPTURES.findall(c["body"]):
            found[(kind, ident)] = c  # git lists newest first: the last write is the oldest
    return found


def first(repo: Path, *args: str) -> dict | None:
    """The oldest non-merge commit `git log <args>` selects, or None."""
    found = _commits(_git(repo, "log", "--no-merges", f"--format={_FORMAT}", *args))
    return found[-1] if found else None


def rule_since(guidance: Path) -> str | None:
    """When the guidance first told agents to route a lesson to a check, skill
    or section: the older of the routing sentence and the section heading."""
    dates = [c["date"] for c in (first(guidance, "-S", n, "--", BASE_MD)
                                 for n in (RULE_HEADING, RULE_FALLBACK)) if c]
    return min(dates) if dates else None


def _record(kind: str, ident: str, commit: dict | None, method: str, rule: str | None,
            impact: dict) -> dict:
    if commit is None:
        return {"kind": kind, "id": ident, "origin": None, "created": None, "commit": None,
                "method": None, "under_rule": None, "impact": impact}
    return {"kind": kind, "id": ident, "origin": origin(commit), "created": commit["date"],
            "commit": commit["sha"][:12], "method": method,
            "under_rule": commit["date"] >= rule if rule else None,
            "impact": impact}


def build(doc: dict, guidance: Path | None, registries: dict, manifest: list | None) -> dict:
    """The `agent_made` block for an explorer document `doc`.

    `guidance` is the _agent-guidance checkout; `registries` maps a registry
    name to its checkout path; `manifest` is agents-md/eval-coverage.yml's rows.
    Any of them missing or shallow leaves those subjects' origin unknown.
    """
    g_ok = usable(guidance)
    rule = rule_since(guidance) if g_ok else None
    g_caps = captures(guidance) if g_ok else {}
    reg_ok = {name: Path(path) for name, path in registries.items() if usable(Path(path))}
    reg_caps = {name: captures(path) for name, path in reg_ok.items()}
    items: list[dict] = []

    for chk in (doc.get("hooks") or {}).get("checks") or []:
        if chk.get("where") != "fleet":
            continue
        ident = chk["name"]
        totals = chk.get("window_totals") or {}
        impact = {"runs": totals.get("invocations"), "blocked": totals.get("blocked"),
                  "verdict": chk.get("verdict")}
        commit, method = g_caps.get(("check", ident)), "trailer"
        if commit is None and g_ok:
            commit, method = first(guidance, "-S", ident, "--", CHECKS_DIR), "first-appearance"
        items.append(_record("check", ident, commit, method, rule, impact))

    for sk in doc.get("skills") or []:
        ident, reg = sk["name"], sk.get("registry")
        impact = {"invocations": (sk.get("usage") or {}).get("invocations"),
                  "verdict": sk.get("verdict")}
        commit, method = (reg_caps.get(reg) or {}).get(("skill", ident)), "trailer"
        if commit is None and reg in reg_ok:
            commit, method = first(reg_ok[reg], "--diff-filter=A", "--",
                                   f"plugins/*/skills/{ident}/SKILL.md",
                                   f"skills/{ident}/SKILL.md"), "first-add"
        items.append(_record("skill", ident, commit, method, rule, impact))

    files = {r["id"]: r.get("file", BASE_MD) for r in (manifest or [])
             if isinstance(r, dict) and "id" in r}
    for sec in (doc.get("guidance") or {}).get("sections") or []:
        ident = sec["id"]
        impact = {"verdict": sec.get("verdict"), "current_text_runs": sec.get("current_text_runs")}
        commit, method = g_caps.get(("section", ident)), "trailer"
        if commit is None and g_ok and sec.get("heading"):
            commit, method = first(guidance, "-S", f"## {sec['heading']}", "--",
                                   files.get(ident, BASE_MD)), "first-appearance"
        items.append(_record("section", ident, commit, method, rule, impact))

    items.sort(key=lambda i: (KINDS.index(i["kind"]), i["id"]))
    return {"rule_since": rule, "items": items, "summary": summarize(items)}


def summarize(items: list[dict]) -> dict:
    """Counts by kind and origin, and the agent-made items' summed impact."""
    out: dict = {}
    for kind in KINDS:
        mine = [i for i in items if i["kind"] == kind]
        agent = [i for i in mine if i["origin"] == "agent"]
        counts = {o: sum(1 for i in mine if i["origin"] == o) for o in ("agent", "loop", "person")}
        counts["unknown"] = sum(1 for i in mine if i["origin"] is None)
        verdicts: dict = {}
        for i in agent:
            v = i["impact"].get("verdict") or "none"
            verdicts[v] = verdicts.get(v, 0) + 1
        row = {"total": len(mine), "by_origin": counts,
               "agent_under_rule": sum(1 for i in agent if i["under_rule"]),
               "agent_verdicts": dict(sorted(verdicts.items()))}
        if kind == "check":
            row["agent_runs"] = sum(i["impact"].get("runs") or 0 for i in agent)
            row["agent_blocked"] = sum(i["impact"].get("blocked") or 0 for i in agent)
        if kind == "skill":
            row["agent_invocations"] = sum(i["impact"].get("invocations") or 0 for i in agent)
        out[kind] = row
    return out
