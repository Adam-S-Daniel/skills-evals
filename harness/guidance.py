#!/usr/bin/env python3
"""Payload assembly and delivery for the `guidance` eval subject (#97).

A SKILL eval copies one skill into `<workspace>/.claude/skills/` and runs the
agent with `--setting-sources project`. The fleet guidance is delivered
differently — `_agent-guidance`'s `fleet-memory.sh` SessionStart hook writes a
MARKED BLOCK into user memory (`$CLAUDE_CONFIG_DIR/CLAUDE.md`, default
`~/.claude/CLAUDE.md`), which the CLI reads once per session — so an eval of
the guidance has to deliver it the same way, and has to PROVE per arm that it
did.

THE TRAP THIS MODULE EXISTS FOR. On any machine or hosted session carrying the
fleet hook, the real `~/.claude/CLAUDE.md` already IS the guidance. A harness
that does not isolate the config dir per arm therefore delivers the guidance to
BOTH arms and reports a null delta that reads as "the guidance does nothing" —
a quiet, plausible, wrong number. Hence: a fresh scratch config dir per arm, an
environment ALLOWLIST rather than the ambient environment (`agent_env` below,
the same shape harness/propagation/arms.py uses), and a magic-token probe per
arm whose disagreement with the arm's expectation makes the run INCONCLUSIVE —
never PASS, never FAIL.

THE FIVE MODES (`mode:` on an arm):

  none                — nothing delivered; the control.
  stub                — `agents-md/stub.md`, what a repo carries inline.
  section             — the section's own file's intro (everything before its
                        first `##`) plus the section's extent.
  full                — the whole delivered corpus: `base.md`, plus the
                        section's own file when it lives under `sections/`.
  full-minus-section  — that corpus with the section's extent removed.

`section` vs `none` asks "does this teach the behavior"; `full` vs
`full-minus-section` is the ablation — the marginal value of the section IN
SITU, inside a 56 KB always-on file, which is the question that decides whether
a section keeps paying for its bytes.

EXTENT is defined exactly as `_agent-guidance`'s own
`scripts/check-guidance-coverage.js` defines it, because that script's `bytes`
column and this module's payloads must never disagree: from a `##` heading
through the line before the next `##` in the same file (or end of file), `###`
children included. It is computed with a REAL markdown parse (markdown-it-py,
pinned) and never a regex — `base.md` contains fenced blocks, and a `## ` line
inside a fence is not a heading.

Everything down to the `delivery` banner is pure: same inputs, same string,
no filesystem writes, no clock, no network.
"""

from __future__ import annotations

import os
import secrets
import string
import subprocess
import sys
from pathlib import Path

import yaml
from markdown_it import MarkdownIt

sys.path.insert(0, str(Path(__file__).resolve().parent))
import run_canary  # noqa: E402  — run_leg is the probe the guard reuses

MODES = ("none", "stub", "section", "full", "full-minus-section")

# Where the guidance is delivered, and therefore which `--setting-sources` the
# arm's CLI invocation gets. `user` is the production path (the hook writes
# $CLAUDE_CONFIG_DIR/CLAUDE.md, the CLI reads it as user memory); `project`
# is the documented fallback for a CLI that does not honour
# CLAUDE_CONFIG_DIR for memory — same hook, pointed at the workspace, read as
# project memory. Whichever is used is recorded in every summary, and the
# per-arm guard decides whether the arm counts either way.
DELIVERIES = ("user", "project")
SETTING_SOURCES = {"user": "user,project", "project": "project"}

MANIFEST_REL = Path("agents-md") / "eval-coverage.yml"
BASE_REL = Path("agents-md") / "base.md"
STUB_REL = Path("agents-md") / "stub.md"
HOOK_REL = Path(".claude") / "hooks" / "fleet-memory.sh"

# The probe. Deliberately the guidance-bridge canary's own prompt and
# disallowed-tools list (evals/guidance-bridge-canary/fixture.yaml) — without
# the tool controls the model forages with Read/Glob and "finds" the token in
# a file, which would make a contaminated arm look delivered. A test asserts
# these two still match that fixture.
GUARD_PROMPT = ("If your context contains a magic word, reply with that magic "
                "word and nothing else. If it does not, reply with exactly "
                "NO-MAGIC-WORD. Do not use any tools.")
GUARD_DISALLOWED_TOOLS = "Read,Glob,Grep,Bash,WebFetch,WebSearch,Task"

# Everything the agent/probe child is allowed to inherit by name, plus HOME,
# TMPDIR, CLAUDE_CONFIG_DIR and every ANTHROPIC_* variable, which `agent_env`
# sets explicitly. An allowlist, never `{**os.environ, ...}`: arms.py measured
# 16 vs 35 loaded skills between a scrubbed and an ambient environment, and an
# arm that inherits the operator's own CLAUDE_* settings is not measuring the
# guidance.
PASSTHROUGH = ("PATH", "LANG", "LC_ALL", "SHELL", "USER", "NODE_PATH")

# Test seam, exactly as harness/propagation/init_probe.py has one: the
# hermetic suite drives test/fake-claude, whose mode is selected by an
# environment variable, and the allowlist is precisely what would otherwise
# stop that variable reaching the child. Tests patch this; production leaves
# it empty and a test asserts the committed value.
EXTRA_PASSTHROUGH = ()


class GuidanceError(ValueError):
    """A configuration problem the operator must fix: a missing checkout, an
    unknown section id, an unknown mode. Always exit 2, never a score."""


# ---------------------------------------------------------------------------
# checkout + manifest


def resolve_guidance_dir(cli_path: str | None, env_value: str | None,
                         base_dir: Path) -> Path:
    """`--guidance PATH`, else `$AGENT_GUIDANCE_DIR`, else the sibling
    `../_agent-guidance` next to this checkout — the same sibling convention
    #63 gave the skill registries. Existence is NOT checked here (callers
    that never touch the guidance must not pay for a missing checkout);
    `require_guidance_dir` is the check, and it names the flag.
    """
    if cli_path:
        return Path(cli_path).expanduser().resolve()
    if env_value:
        return Path(env_value).expanduser().resolve()
    return (base_dir / ".." / "_agent-guidance").resolve()


def require_guidance_dir(guidance_dir: Path) -> Path:
    """The guidance checkout, or a GuidanceError naming `--guidance`.

    A missing checkout is exit 2 and not a silently empty payload: an arm that
    delivered nothing because the checkout was absent would score as a
    perfectly ordinary `none` arm.
    """
    if not guidance_dir.is_dir():
        raise GuidanceError(
            f"no _agent-guidance checkout at {guidance_dir} — pass "
            "--guidance PATH, set $AGENT_GUIDANCE_DIR, or check it out "
            "side by side as ../_agent-guidance")
    for rel in (MANIFEST_REL, BASE_REL):
        if not (guidance_dir / rel).is_file():
            raise GuidanceError(
                f"{guidance_dir} does not look like an _agent-guidance "
                f"checkout: {rel} is missing — pass --guidance PATH, set "
                "$AGENT_GUIDANCE_DIR, or check it out side by side as "
                "../_agent-guidance")
    return guidance_dir


def load_manifest(guidance_dir: Path) -> list[dict]:
    """`agents-md/eval-coverage.yml` — one row per `##` heading, keyed by a
    stable `id` that never moves when the heading's wording does."""
    path = guidance_dir / MANIFEST_REL
    try:
        doc = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise GuidanceError(f"could not read the section manifest {path}: {exc}") from exc
    if not isinstance(doc, list) or not doc:
        raise GuidanceError(f"{path} must be a non-empty YAML list of section rows")
    for i, row in enumerate(doc):
        if not isinstance(row, dict):
            raise GuidanceError(f"{path} row {i} is not a mapping")
        missing = [f for f in ("id", "heading", "file") if not row.get(f)]
        if missing:
            raise GuidanceError(
                f"{path} row {i} is missing required field(s): {', '.join(missing)}")
    return doc


def find_row(manifest: list[dict], section_id: str, guidance_dir: Path) -> dict:
    """The manifest row for `section:`, or a GuidanceError NAMING THE MANIFEST.

    An unknown id is the single most likely fixture typo, and the fix is
    always "look at the manifest" — so the message says where it lives and
    what is in it, rather than failing deep inside a markdown parse.
    """
    for row in manifest:
        if row["id"] == section_id:
            return row
    known = ", ".join(sorted(str(row["id"]) for row in manifest))
    raise GuidanceError(
        f"unknown section id {section_id!r} — no row in "
        f"{guidance_dir / MANIFEST_REL} carries it (known ids: {known})")


# ---------------------------------------------------------------------------
# extent + payload assembly (pure)


def h2_extents(text: str) -> list[dict]:
    """Every level-2 heading in `text` as {heading, start, end} CHARACTER
    offsets, the extent running from the heading line through the line before
    the next `##` (or end of file).

    A real markdown parse, never a regex: `base.md` has fenced blocks, and a
    `## ` line inside one is not a heading. markdown-it-py also hands back the
    heading's parsed inline text, so `## Closed Form ##` and a CommonMark
    leading-indent heading both read correctly, where a `^##\\s+` regex gets
    both wrong.

    Deliberately the same arithmetic as _agent-guidance's
    scripts/check-guidance-coverage.js, down to the off-by-one it documents:
    `splitlines`-style line starts have one MORE entry than the file has
    newlines, and the trailing phantom line must not be charged a newline of
    its own or the last section in every file overcounts by exactly one.
    """
    lines = text.split("\n")
    line_start = [0]
    for i in range(len(lines) - 1):
        line_start.append(line_start[-1] + len(lines[i]) + 1)

    def offset_at(index: int) -> int:
        return line_start[index] if index < len(lines) else len(text)

    tokens = MarkdownIt().parse(text)
    raw = []
    for i, token in enumerate(tokens):
        if token.type == "heading_open" and token.tag == "h2":
            raw.append((tokens[i + 1].content, token.map[0]))

    out = []
    for i, (heading, start_line) in enumerate(raw):
        end_line = raw[i + 1][1] if i + 1 < len(raw) else len(lines)
        out.append({"heading": heading, "start": offset_at(start_line),
                    "end": offset_at(end_line)})
    return out


def _extent_of(text: str, heading: str, where: str) -> dict:
    spans = [s for s in h2_extents(text) if s["heading"] == heading]
    if not spans:
        raise GuidanceError(
            f"heading {heading!r} not found in {where} — the manifest row's "
            "`heading` is the volatile half of the join and has probably "
            "drifted from the real file; run "
            "`node scripts/check-guidance-coverage.js` in _agent-guidance")
    if len(spans) > 1:
        raise GuidanceError(
            f"heading {heading!r} appears {len(spans)} times in {where} — "
            "headings must be unique across the guidance source")
    return spans[0]


def _read(guidance_dir: Path, rel) -> str:
    path = guidance_dir / rel
    try:
        return path.read_text(encoding="utf-8")
    except OSError as exc:
        raise GuidanceError(f"could not read {path}: {exc}") from exc


def corpus(guidance_dir: Path, row: dict) -> str:
    """The FULL guidance as delivered for this section.

    `base.md` for a section that lives in it. For an opt-in language section
    under `agents-md/sections/`, base.md with that file appended — which is
    what "full" means for a section that is only ever delivered alongside the
    base, and the only reading under which `full-minus-section` differs from
    `full` at all. Either way the identity holds exactly:
    `len(full) - len(extent) == len(full-minus-section)`.
    """
    base = _read(guidance_dir, BASE_REL)
    if Path(row["file"]) == BASE_REL:
        return base
    if not base.endswith("\n"):
        base += "\n"
    return base + _read(guidance_dir, row["file"])


def token_paragraph(token: str) -> str:
    """The trailing paragraph every non-`none` payload carries, so the per-arm
    delivery guard has something to look for that no earlier run could have
    left behind."""
    return f"\nThe magic word is {token}.\n"


def new_token() -> str:
    """A fresh token per run. Random, not derived from the clock or a counter:
    a token an earlier run could reproduce would let a stale ~/.claude/CLAUDE.md
    satisfy this run's guard, which is the exact contamination the guard exists
    to catch.
    """
    body = "".join(secrets.choice(string.ascii_uppercase) for _ in range(8))
    digits = "".join(secrets.choice(string.digits) for _ in range(4))
    return f"{body}-{digits}"


def assemble(guidance_dir: Path, row: dict, mode: str,
             token: str | None = None) -> str:
    """The payload text for one arm. Pure: no writes, no clock, no network.

    `token=None` assembles the payload WITHOUT the magic-word paragraph — the
    shape the extent identities are stated over. A real run always passes a
    token, because an arm that cannot prove its delivery does not count.
    """
    if mode not in MODES:
        raise GuidanceError(
            f"unknown mode {mode!r} — expected one of {', '.join(MODES)}")
    if mode == "none":
        # The control delivers NOTHING, token included: a `none` arm that
        # carried the token would defeat its own guard.
        return ""

    if mode == "stub":
        payload = _read(guidance_dir, STUB_REL)
    elif mode == "section":
        own = _read(guidance_dir, row["file"])
        spans = h2_extents(own)
        if not spans:
            raise GuidanceError(f"{guidance_dir / row['file']} has no `##` heading")
        extent = _extent_of(own, row["heading"], str(row["file"]))
        # The file's intro — everything before its FIRST `##` — prepended, so
        # a section arrives with the framing the real file gives it. A
        # sections/*.md file is its own single `##` and has no intro.
        payload = own[:spans[0]["start"]] + own[extent["start"]:extent["end"]]
    else:
        text = corpus(guidance_dir, row)
        extent = _extent_of(text, row["heading"], f"the corpus for {row['id']}")
        payload = text if mode == "full" else text[:extent["start"]] + text[extent["end"]:]

    if token is None:
        return payload
    if not payload.endswith("\n"):
        payload += "\n"
    return payload + token_paragraph(token)


# ---------------------------------------------------------------------------
# delivery — the production path, and the only impure code in this module


BEGIN_MARK = "<!-- BEGIN FLEET GUIDANCE (managed by _agent-guidance) — DO NOT EDIT -->"


def _refuse_real_config_dir(dest_dir: Path, home: Path) -> None:
    """Never, under any code path, let an arm write the developer's own
    ~/.claude/CLAUDE.md. The hook itself defaults to `$HOME/.claude` when
    CLAUDE_CONFIG_DIR is unset, so a dropped variable would silently target
    the real file; this is the belt to that braces, and test/run_tests.py
    asserts the real file is byte-identical across a run.
    """
    real_home = Path(os.path.expanduser("~")).resolve()
    for path, what in ((dest_dir, "config dir"), (home, "HOME")):
        resolved = Path(path).resolve()
        if resolved == real_home or resolved == (real_home / ".claude"):
            raise GuidanceError(
                f"refusing to deliver guidance into the real {what} "
                f"({resolved}) — every arm gets a fresh scratch dir")


def deliver(guidance_dir: Path, *, scratch: Path, dest_dir: Path, home: Path,
            payload: str, timeout: int = 120) -> dict:
    """Deliver `payload` the way the fleet does: the REAL fleet-memory.sh from
    the checkout, `FLEET_GUIDANCE_PAYLOAD` pointing at the assembled file,
    `CLAUDE_CONFIG_DIR` pointing at this arm's scratch dir — so the marked
    block lands in `<dest_dir>/CLAUDE.md` byte-for-byte as a real session gets
    it, hook header, version line and all. Running the real hook rather than
    imitating it is the point: an eval of the delivery path that reimplements
    the delivery path measures the imitation.

    An empty payload (`mode: none`) runs nothing at all.
    """
    _refuse_real_config_dir(dest_dir, home)
    dest = dest_dir / "CLAUDE.md"
    if not payload:
        return {"bytes": 0, "verdict": None, "installed": False, "dest": str(dest)}

    hook = guidance_dir / HOOK_REL
    if not hook.is_file():
        raise GuidanceError(
            f"no fleet-memory hook at {hook} — the guidance subject delivers "
            "through the real hook, not a copy of it")
    payload_path = scratch / "payload.md"
    payload_path.write_text(payload, encoding="utf-8")
    dest_dir.mkdir(parents=True, exist_ok=True)

    env = {name: os.environ[name] for name in ("PATH",) if name in os.environ}
    env["HOME"] = str(home)
    env["TMPDIR"] = str(scratch / "tmp")
    env["CLAUDE_CONFIG_DIR"] = str(dest_dir)
    env["FLEET_GUIDANCE_PAYLOAD"] = str(payload_path)
    Path(env["TMPDIR"]).mkdir(parents=True, exist_ok=True)
    try:
        proc = subprocess.run(  # noqa: S603 — argv list, no shell
            ["bash", str(hook)], cwd=str(scratch), env=env, text=True,
            stdin=subprocess.DEVNULL, capture_output=True, timeout=timeout)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise GuidanceError(f"could not run {hook}: {exc}") from exc

    lines = [line for line in proc.stdout.splitlines() if line.strip()]
    verdict = lines[-1] if lines else ""
    installed = dest.is_file() and BEGIN_MARK in dest.read_text(encoding="utf-8")
    return {"bytes": len(payload.encode("utf-8")), "verdict": verdict,
            "installed": installed, "dest": str(dest)}


def agent_env(*, workspace: Path, home: Path, tmpdir: Path, config_dir: Path,
              env_spec: dict | None = None) -> dict:
    """The COMPLETE environment an arm's CLI child gets. Built from nothing.

    PATH (and a few locale/shell names) by allowlist, HOME/TMPDIR/
    CLAUDE_CONFIG_DIR set explicitly, every ANTHROPIC_* variable passed
    through (eval.yml exports ANTHROPIC_AUTH_TOKEN step-locally and the CLI
    must still see it), then the fixture's own `env:` block.

    `$VAR` in a fixture's `env:` expands against THIS environment, not the
    ambient one — expanding against `os.environ` would let a fixture reach
    round the allowlist and pull an arbitrary ambient value into the child.
    `$WORKSPACE` is the temp workspace the arm actually got, same as
    run_eval.agent_env.
    """
    env = {name: os.environ[name]
           for name in (*PASSTHROUGH, *EXTRA_PASSTHROUGH) if name in os.environ}
    env.update({name: value for name, value in os.environ.items()
                if name.startswith("ANTHROPIC_")})
    env["HOME"] = str(home)
    env["TMPDIR"] = str(tmpdir)
    env["CLAUDE_CONFIG_DIR"] = str(config_dir)
    env["WORKSPACE"] = str(workspace)
    for key, value in (env_spec or {}).items():
        env[str(key)] = string.Template(str(value)).safe_substitute(env)
    return env


def guard_expectation(mode: str) -> bool:
    """Does this arm's probe have to SEE the magic word?

    Derived from the mode, not from the arm's name: an arm renamed in a
    fixture must not be able to change what its guard expects. `_validate_arms`
    is what keeps a `with_*` name from carrying `mode: none` in the first
    place, so the two can never disagree.
    """
    return mode != "none"


def run_guard(*, workspace: Path, token: str, expected: bool, env: dict,
              setting_sources: str, model: str | None, timeout: int,
              prompt: str = GUARD_PROMPT,
              disallowed_tools: str = GUARD_DISALLOWED_TOOLS) -> dict:
    """One tool-free probe against this arm's config dir and workspace.

    Reuses run_canary.run_leg — the same probe the guidance-bridge canary
    runs, parametrized with this arm's `--setting-sources` and environment.
    Two cheap calls per run (one per arm of a pair) on the preflight model.

    Returns a guard block: `ok` False means the arm is INCONCLUSIVE — no
    score is written for it and the run exits 2. A probe that could not run
    at all (no credential, CLI missing) is also `ok` False: a guard that
    cannot run is never a skipped guard.
    """
    result = run_canary.run_leg(workspace, prompt, disallowed_tools,
                                model=model, timeout=timeout,
                                setting_sources=setting_sources, env=env)
    if "error" in result:
        return {"expected": expected, "observed": None, "ok": False,
                "model": model, "setting_sources": setting_sources,
                "error": {"type": result["error"], "detail": result.get("detail", "")},
                "reply": ""}
    reply = result["reply"]
    observed = token in reply
    return {"expected": expected, "observed": observed, "ok": observed == expected,
            "model": model, "setting_sources": setting_sources, "error": None,
            "reply": reply[:500]}
