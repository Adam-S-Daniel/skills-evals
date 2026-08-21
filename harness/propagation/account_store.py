#!/usr/bin/env python3
"""Tier 3: audit the claude.ai account skill store against the registry.

The account store is the one delivery channel CI structurally cannot see: it
lands at `~/.claude/skills/synced/` and only exists on a surface where an
account is signed in. That is a SURFACE constraint, not a credential one —
nothing in this module spawns the CLI, calls an API, or spends anything. It
reads files.

Why it is worth a scheduled run at all: the store drifts on its own, silently,
with no event anyone sees. Measured on this box, the account copies of the
registry-owned skills carry `updatedAt` values from 2026-04-05 to 2026-08-13 —
several months behind the registry — and only the **description** reaches the
model's context, so a stale description means a skill that quietly stops
triggering while still appearing to be installed.

Scope of that harm, measured 2026-08-20 in agentskills
`docs/experiments/E5-account-store-vs-hook-precedence.md`: **where a skill is
delivered by both channels, the SessionStart hook's copy wins** — two cloud
sessions, the Skill tool naming `~/.claude/skills/<name>/` as its base
directory, the name listed once rather than twice. So a stale account copy is
shadowed wherever the hook runs, and live everywhere it does not: chat, Cowork,
Claude in Chrome, mobile, and any multi-repo Claude Code session (agentskills
#84). That is the inverse of where the verification is — the drifting channel
serves the surfaces nothing checks — and it is why this audit is not made
redundant by a green bootstrap verdict.

The same experiment found the drift concentrated where nothing could have
caught it: of ten account copies exactly one had drifted, and it was in
`adam-local`, the one bundle no `skills.lock` ships and therefore no digest
ever re-verifies.

Two traps this module is built around:

* **CRLF.** Account copies arrive with CRLF line endings; the registry is LF.
  Without normalisation the content comparison false-positives on files whose
  bytes are otherwise identical, and a check with a known false-positive rate
  gets muted rather than fixed. Every content digest here normalises CRLF→LF
  first. `test_crlf_only_difference_is_not_drift` locks that in.
* **Timestamps are not evidence.** `updatedAt` vs "the registry's last commit
  touching this directory" reports a skill as months stale when the only
  intervening commit moved the directory without changing a byte. The digest
  is the assertion; the timestamp is reported only as human-readable colour.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

import yaml

MANIFEST_RELPATH = Path(".claude") / "skills" / "synced" / "manifest.json"
# Never compared: build detritus that no upload would ever carry.
IGNORED_NAMES = ("__pycache__", ".git", ".DS_Store")


class AuditError(RuntimeError):
    """The audit could not run — reported as a fault, never as a clean pass."""


@dataclass
class SkillFinding:
    skill: str
    kind: str
    detail: str


@dataclass
class AuditResult:
    checked: list = field(default_factory=list)
    findings: list = field(default_factory=list)
    skipped: list = field(default_factory=list)

    @property
    def status(self) -> str:
        return "pass" if not self.findings else "fail"


def normalise(data: bytes) -> bytes:
    """CRLF → LF. The account store's line endings are not a content change."""
    return data.replace(b"\r\n", b"\n")


def content_digest(files: dict) -> str:
    """sha256 over `{relpath: normalised bytes}`, sorted by relpath."""
    manifest = "".join(
        f"{relpath}\0{hashlib.sha256(normalise(data)).hexdigest()}\n"
        for relpath, data in sorted(files.items()))
    return hashlib.sha256(manifest.encode("utf-8")).hexdigest()


def read_tree(root: Path) -> dict:
    """{relpath: bytes} for every file under `root`, minus IGNORED_NAMES."""
    out = {}
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        parts = path.relative_to(root).parts
        if any(part in IGNORED_NAMES for part in parts):
            continue
        out["/".join(parts)] = path.read_bytes()
    return out


def git_tracked(root: Path, subdir: Path) -> set | None:
    """What git has under `subdir`, or None when `root` is not a git checkout.

    Preferred over a filesystem walk for the registry side: it is the
    authoritative "what would be uploaded" set and it inherits .gitignore
    instead of restating it.
    """
    try:
        proc = subprocess.run(  # noqa: S603 — argv list, no shell
            ["git", "-C", str(root), "ls-files", "-z", "--", str(subdir)],
            capture_output=True, timeout=60)
    except (OSError, subprocess.TimeoutExpired):
        return None
    if proc.returncode != 0:
        return None
    rel = subdir.relative_to(root).as_posix() if subdir.is_absolute() else str(subdir)
    prefix = rel.rstrip("/") + "/"
    return {name[len(prefix):]
            for name in proc.stdout.decode("utf-8", "replace").split("\0")
            if name.startswith(prefix)}


def frontmatter(text: str) -> dict:
    """The SKILL.md YAML frontmatter, parsed with a real YAML parser.

    The `---` fences are DOCUMENT FRAMING, located by line, exactly as the
    skill format defines them; what sits between them is handed to
    `yaml.safe_load`. No field is ever read with a regex — an unquoted `: ` in
    a description is precisely the kind of thing that makes a hand-rolled
    reader disagree with the loader that actually decides whether the skill
    loads.
    """
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        raise AuditError("no YAML frontmatter (first line is not `---`)")
    for index in range(1, len(lines)):
        if lines[index].strip() == "---":
            block = "\n".join(lines[1:index])
            break
    else:
        raise AuditError("frontmatter fence is never closed")
    try:
        parsed = yaml.safe_load(block)
    except yaml.YAMLError as exc:
        raise AuditError(f"frontmatter is not valid YAML: {exc}") from exc
    if not isinstance(parsed, dict):
        raise AuditError(f"frontmatter parsed as {type(parsed).__name__}, not a mapping")
    return parsed


def read_manifest(home: Path) -> list:
    path = home / MANIFEST_RELPATH
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise AuditError(
            f"no account store at {path} — this surface has no signed-in "
            "account, so the account channel cannot be audited from here. "
            "That is a surface limitation, not a clean result.") from exc
    except (OSError, json.JSONDecodeError) as exc:
        raise AuditError(f"could not read {path}: {exc}") from exc
    skills = payload.get("skills")
    if not isinstance(skills, list):
        raise AuditError(f"{path} carries no `skills` list")
    return [s for s in skills if isinstance(s, dict) and s.get("name")]


def registry_skill_dir(registry: Path, name: str) -> Path | None:
    """`plugins/*/skills/<name>` — the same glob run_eval.py resolves with."""
    matches = sorted(p for p in (registry / "plugins").glob(f"*/skills/{name}")
                     if p.is_dir())
    return matches[0] if matches else None


def audit(home: Path, registry: Path) -> AuditResult:
    """Compare every account copy that the registry also owns."""
    if not (registry / "plugins").is_dir():
        raise AuditError(f"{registry} does not look like an agentskills checkout "
                         "(no plugins/ directory)")
    result = AuditResult()
    store = home / MANIFEST_RELPATH.parent
    for record in read_manifest(home):
        name = record["name"]
        source = registry_skill_dir(registry, name)
        if source is None:
            # An account skill the registry does not own (Anthropic examples,
            # one-offs). Not drift, and not this audit's business.
            result.skipped.append(name)
            continue
        account_dir = store / name
        if not account_dir.is_dir():
            result.findings.append(SkillFinding(
                name, "account-copy-missing",
                f"the manifest lists {name} but {account_dir} does not exist"))
            continue

        result.checked.append(name)
        account_files = read_tree(account_dir)
        registry_files = read_tree(source)
        tracked = git_tracked(registry, source)
        if tracked is not None:
            registry_files = {rel: data for rel, data in registry_files.items()
                              if rel in tracked}

        missing = sorted(set(registry_files) - set(account_files))
        if missing:
            result.findings.append(SkillFinding(
                name, "missing-payload",
                f"the account copy is missing {missing} — a session activating "
                "it is told to run files that are not there"))

        if content_digest(account_files) != content_digest(registry_files):
            differing = sorted(
                rel for rel in set(account_files) & set(registry_files)
                if normalise(account_files[rel]) != normalise(registry_files[rel]))
            result.findings.append(SkillFinding(
                name, "content-drift",
                f"CRLF-normalised content differs in {differing or '(file set)'}; "
                f"account updatedAt={record.get('updatedAt')}"))

        skill_md = account_files.get("SKILL.md")
        if skill_md is None:
            result.findings.append(SkillFinding(
                name, "no-skill-md", "the account copy has no SKILL.md"))
            continue
        try:
            # A skill whose frontmatter will not parse is DELIVERED and
            # INVISIBLE: it can still register a slash command while never
            # entering the model's skill list. Nothing else in this programme
            # catches that, which is why it is an assertion and not a comment.
            frontmatter(normalise(skill_md).decode("utf-8", "replace"))
        except AuditError as exc:
            result.findings.append(SkillFinding(
                name, "unparseable-frontmatter", str(exc)))
            continue

        # The description of record is the one assertion with BEHAVIOURAL
        # teeth, and the PAIR matters: what the ACCOUNT serves (the manifest
        # description — the string that reaches the model's context and decides
        # whether the skill triggers at all) against what the REGISTRY declares.
        # Comparing the manifest to the account's own SKILL.md instead would
        # only prove the store is internally consistent, which it is even when
        # it is months out of date — a check that cannot see the incident it
        # was written for. `test_an_internally_consistent_but_stale_store_is_
        # still_drift` is the mutation that holds this pair in place.
        try:
            declared = frontmatter(
                (source / "SKILL.md").read_text(encoding="utf-8"))
        except (OSError, AuditError) as exc:
            result.findings.append(SkillFinding(
                name, "registry-description-unreadable",
                f"cannot compare descriptions: the registry copy at {source} "
                f"is unreadable ({exc})"))
            continue

        of_record = str(record.get("description") or "").strip()
        expected = str(declared.get("description") or "").strip()
        if of_record != expected:
            result.findings.append(SkillFinding(
                name, "description-drift",
                "the description claude.ai serves is not the one the registry "
                f"declares ({len(of_record)} vs {len(expected)} chars) — only "
                "the description gates invocation, so this skill triggers "
                "differently on claude.ai than everywhere else"))
    return result


def summarise(result: AuditResult, *, generated_at: str, registry_ref: str) -> dict:
    """The published record. Consumed by the PR-side freshness gate."""
    return {
        "schema": 1,
        "probe": "propagation/account",
        "status": result.status,
        "generated_at": generated_at,
        "registry_ref": registry_ref,
        "checked": sorted(result.checked),
        "skipped": sorted(result.skipped),
        "findings": [vars(f) for f in sorted(result.findings,
                                             key=lambda f: (f.skill, f.kind))],
    }


def badge(summary: dict) -> dict:
    """shields.io endpoint JSON — same transport as scripts/make_badge.py."""
    checked = len(summary.get("checked") or [])
    skills = {f["skill"] for f in summary.get("findings") or []}
    date = str(summary.get("generated_at", ""))[:10]
    if summary.get("status") == "pass":
        message, color = f"{checked} in sync · {date}", "green"
    else:
        message, color = f"{len(skills)} of {checked} drifted · {date}", "red"
    return {"schemaVersion": 1, "label": "account skill store",
            "message": message, "color": color}


# ---------------------------------------------------------------------------
# the freshness gate — how a red SCHEDULED run reaches a human


def parse_iso8601(value: str) -> datetime:
    text = str(value).strip().replace("Z", "+00:00")
    parsed = datetime.fromisoformat(text)
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def freshness_verdict(summary: dict | None, *, now: datetime, max_age_days: int,
                      bootstrapped: bool) -> tuple:
    """(ok, status, message) for the PR-side gate that watches the Routine.

    This is the single most important line of the Tier-3 design: a scheduled
    job that fails notifies nobody, and one that simply STOPS FIRING notifies
    nobody twice over. So the credential-free PR gate reads the audit's last
    published result and reds the next pull request when it is missing, stale,
    or unreadable. The schedule is watched by something that cannot be ignored.

    This function reports what is TRUE and does not decide what blocks. The
    caller does: `run_propagation.run_gate` downgrades `reported-failure` to a
    WARN on pull requests, because a red verdict is the ACCOUNT store drifting
    and no commit in this repo can cause or clear it — a gate that blocks every
    pull request on it gets ignored, then disabled, which is the same death as
    never building it. The liveness statuses above are never downgraded: those
    say the audit is not reaching us, which is the whole point of the gate.

    `bootstrapped` is the bootstrap fix: until the first successful audit
    commits its marker, an absent result is NOT a failure — otherwise this gate
    reds every pull request from the day it merges and gets disabled in week
    one, which is the same death as never building it.
    """
    if summary is None:
        if not bootstrapped:
            return (True, "not-yet-bootstrapped",
                    "the account audit has never published a result; this gate "
                    "starts enforcing once the first Routine run commits "
                    "propagation/.bootstrapped to eval-results")
        return (False, "missing",
                "the account audit published a bootstrap marker but its latest "
                "result is gone — the Routine is broken or someone deleted it")

    status = summary.get("status")
    try:
        generated = parse_iso8601(summary.get("generated_at", ""))
    except (TypeError, ValueError) as exc:
        return (False, "unreadable",
                f"the published result has no readable generated_at: {exc}")

    age_days = (now - generated).total_seconds() / 86400
    if age_days > max_age_days:
        # Three causes, and this function cannot tell them apart: the Routine
        # stopped firing; it fired and its result never landed; or its bound
        # session was silently replaced by one with no repository sources, so
        # it fires and measures but can never push (#47, 2026-08-19). Naming
        # only the first sends the reader to check a schedule that is healthy —
        # 2026-08-14, when three runs measured correctly and every push was
        # refused by the session's repository scope.
        return (False, "stale",
                f"the account audit last ran {age_days:.1f} days ago "
                f"(limit {max_age_days}) — the Routine has stopped firing, "
                "its result is no longer reaching eval-results, or its bound "
                "session was replaced by one with no repository sources "
                "(check session_context.sources; see evals/propagation/ROUTINE.md)")
    if status != "pass":
        skills = sorted({f.get("skill") for f in summary.get("findings") or []})
        return (False, "reported-failure",
                f"the account audit reported {status} {age_days:.1f} days ago: "
                f"{len(skills)} skill(s) drifted — {skills}")
    return (True, "fresh",
            f"the account audit passed {age_days:.1f} days ago "
            f"({len(summary.get('checked') or [])} skill(s) checked)")
