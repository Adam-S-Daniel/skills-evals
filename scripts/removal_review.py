#!/usr/bin/env python3
"""The adversarial review of an automatic removal (skills-evals#917).

scripts/retire_skill.py prepares a `retire-skill/<skill>` or
`retire-guidance/<section>` branch, calls `review` here on it before
anything is pushed, opens the pull request with the result in its body under
`## Adversarial review` (so the registry's first CI run reads it), reads the
body back, and arms auto-merge only when it carries the line

    Adversarial-review: pass <link to the workflow run>

(`has_pass`). Any other result, `block` included, leaves the pull request
open and unarmed for a person. That line is the shared contract: the
registries' own checks (adam-agentskills#133's name-loss check,
_agent-guidance#488's lock-bump hold) accept a removal that carries it.

WHAT IS CHECKED. Two parts, both recorded:

  * `scope_findings`, mechanical and first: every path the removal changes
    must be inside adam-agentskills ADR 0021 Decision 3 (the one subject's
    own directory plus its bookkeeping files) for a skill, or inside the
    files `retire_skill.guidance_prepare_branch` writes for a section. A
    path outside it is a `blocker`, and no reviewer is started.
  * rounds of a fresh-context reviewer (`claude -p`, `MODEL`, a new process
    every round, never a fork of the opener). It gets only the prompt
    `prompt` builds: the subject, the verdict summary, the diff, the
    references `references` found with `git grep`, which checkouts it can
    read, and the target list (other skills, guidance, hooks, docs or
    fixtures that name the subject; consumer `skills.lock` keys the removal
    drops; records keyed by the name; the ADR 0021 scope). Its tools are
    Read, Grep and Glob over those checkouts only: no shell, no network, no
    settings, hooks or MCP from any checkout. Each round after the first is
    also given the findings so far, so it reports only new ones.

THE STOP RULE (the issue's): keep going while a round finds something new;
stop after `QUIET_ROUNDS` (2) consecutive rounds with no new finding of equal
or higher severity than the worst found so far. A `blocker` ends the review
at once (the outcome is `block` whatever later rounds say). `MAX_ROUNDS` (5)
rounds without two quiet ones in a row is `block`: the review did not settle.

OUTCOME. `pass` when no round reported a `blocker` and the rule stopped the
rounds; `block` otherwise. A round that fails in any way (the CLI exits
non-zero, times out, or answers anything but the JSON object asked for) is
`block`, named by its error's type only: unknown never arms.

The findings are model text placed in a public pull request body, so
`section` flattens each to one line, cuts it to `SUMMARY_LIMIT` characters
and HTML-escapes it, with `@` encoded so it can mention no one; a finding
can never start a line, so it cannot forge the `Adversarial-review:` line.

Tests inject `run_round`; nothing here touches the network on its own.
"""

from __future__ import annotations

import html
import json
import os
import re
import subprocess
import tempfile
from pathlib import Path

#: The reviewer's model (the issue: Opus). The roster's Opus.
MODEL = "claude-opus-5-5"
MAX_ROUNDS = 5
QUIET_ROUNDS = 2
#: Per round: the CLI's wall-clock limit and turn limit.
ROUND_TIMEOUT = 900
MAX_TURNS = 60
SEVERITIES = {"note": 1, "blocker": 2}
AREAS = ("references", "locks", "records", "scope", "other")
HEADING = "## Adversarial review"
LINE_PREFIX = "Adversarial-review:"
LINE_RE = re.compile(r"^Adversarial-review: (pass|block) (https://github\.com/\S+)$", re.M)
SUMMARY_LIMIT = 500
DIFF_LIMIT = 60_000
REFERENCE_LIMIT = 200
#: The credential the reviewer's CLI authenticates with in the workflow
#: (the WIF bearer skill-coverage.yml mints, as eval.yml does).
TOKEN_ENV = "ANTHROPIC_AUTH_TOKEN"
#: Only these reach the reviewer's process: no GitHub token, ever.
CHILD_ENV = ("PATH", "HOME", "LANG", "TMPDIR", TOKEN_ENV,
             "HTTPS_PROXY", "HTTP_PROXY", "NO_PROXY", "SSL_CERT_FILE",
             "NODE_EXTRA_CA_CERTS")
TOOLS = "Read,Grep,Glob"

#: adam-agentskills ADR 0021 Decision 3, for a removal: the skill's own
#: directory, `docs/skill-impact.md`, the plugin's two manifests, the README
#: table, `skills.lock`, `scripts/plugin_layout.json`, and the shipped-names
#: ledger (adam-agentskills#133), which a removal appends to.
SKILL_BOOKKEEPING = ("docs/skill-impact.md", "README.md", "skills.lock",
                     "scripts/plugin_layout.json", "scripts/shipped_names.json")
#: What `retire_skill.guidance_prepare_branch` may write besides the
#: section's own file.
GUIDANCE_BOOKKEEPING = ("agents-md/eval-coverage.yml", "docs/guidance-impact.md",
                        "AGENTS.md", ".claude/hooks/fleet-guidance.md")


class ReviewError(Exception):
    """A round that produced no usable answer."""


def check_ready(env) -> None:
    """Refuse before anything is opened when no reviewer can run: no
    credential, or no `claude` on PATH."""
    if not env.get(TOKEN_ENV):
        raise ReviewError(f"no {TOKEN_ENV} for the adversarial review")
    path = env.get("PATH", "")
    if not any(Path(d, "claude").is_file() for d in path.split(os.pathsep) if d):
        raise ReviewError("no claude CLI on PATH for the adversarial review")


def allowed_paths(target: str, subject_path: str, plugin: str | None) -> tuple:
    """(prefixes, exact files) a removal may change."""
    if target == "skill":
        return ((subject_path.rstrip("/") + "/",),
                (*SKILL_BOOKKEEPING, f"plugins/{plugin}/plugin.json",
                 f"plugins/{plugin}/.claude-plugin/plugin.json"))
    return ((), (subject_path, *GUIDANCE_BOOKKEEPING))


def scope_findings(changed: list, target: str, subject_path: str,
                   plugin: str | None = None) -> list:
    """A `blocker` for each changed path outside the allowed set."""
    prefixes, exact = allowed_paths(target, subject_path, plugin)
    return [{"severity": "blocker", "area": "scope",
             "summary": f"the removal changes {p}, outside its subject and bookkeeping "
                        "(adam-agentskills ADR 0021 Decision 3)"}
            for p in changed if p not in exact and not p.startswith(prefixes)]


def _git(checkout: Path, *args: str) -> str:
    return subprocess.run(["git", "-C", str(checkout), *args], check=True,
                          capture_output=True, text=True).stdout


def changed_paths(checkout: Path, base: str) -> list:
    return [p for p in _git(checkout, "diff", "--name-only", "--no-renames",
                            f"{base}..HEAD").splitlines() if p]


def diff_text(checkout: Path, base: str) -> str:
    """Every path's status, then the full diff of every path not deleted
    (a deleted file's lines say nothing about who else names it), cut at
    DIFF_LIMIT characters with a note."""
    status = _git(checkout, "diff", "--name-status", "--no-renames", f"{base}..HEAD")
    body = _git(checkout, "diff", "--no-renames", "--diff-filter=d", f"{base}..HEAD")
    if len(body) > DIFF_LIMIT:
        body = body[:DIFF_LIMIT] + f"\n[diff cut at {DIFF_LIMIT} characters]\n"
    return f"{status}\n{body}"


def references(dirs: dict, terms: list) -> list:
    """`git grep` lines (`<checkout>:<path>:<line>`) naming any term as a
    whole word in each readable checkout, at most REFERENCE_LIMIT."""
    found = []
    for name, path in sorted(dirs.items()):
        args = ["grep", "-n", "-I", "-w", "--fixed-strings"]
        for term in terms:
            args += ["-e", term]
        proc = subprocess.run(["git", "-C", str(path), *args], capture_output=True,
                              text=True)
        if proc.returncode not in (0, 1):
            found.append(f"{name}: git grep failed (exit {proc.returncode})")
            continue
        found += [f"{name}:{line[:300]}" for line in proc.stdout.splitlines()]
    if len(found) > REFERENCE_LIMIT:
        found = found[:REFERENCE_LIMIT] + [f"[cut at {REFERENCE_LIMIT} lines]"]
    return found


def prompt(subject: dict, verdict: str, diff: str, refs: list, dirs: dict,
           prior: list) -> str:
    """The whole of what one round sees. `subject` has `target`, `name`,
    `path`, and for a skill `plugin`."""
    kind = "skill" if subject["target"] == "skill" else "guidance section"
    where = "\n".join(f"- `{n}`: {p}" for n, p in sorted(dirs.items()))
    lock = (f"`{subject['plugin']}/{subject['name']}`" if subject["target"] == "skill"
            else "none (a guidance section has no lock key)")
    seen = ("\n".join(f"- [{f['severity']}/{f['area']}] {f['summary']}" for f in prior)
            if prior else "none yet")
    return f"""You are reviewing an automatic removal pull request before it is allowed
to merge with no human review. Your job is to find what this removal breaks
or leaves wrong elsewhere, not to approve it. You did not write it.

Subject: the {kind} `{subject['name']}` at `{subject['path']}`.
The statistical verdict (already decided; do not re-argue it): {verdict}

Checkouts you can read (Read, Grep and Glob only; the removal branch is
checked out in the registry, so the subject is already gone there):
{where}
Repositories not listed are not readable here; say so rather than guess.

Check each of these and report what you find:
1. references: other skills, guidance sections, hooks, docs, scripts, tests
   or fixtures that still name `{subject['name']}` and will dangle or
   mislead once it is gone.
2. locks: consumer `skills.lock` entries that lose the key {lock}. Losing it
   is the intended effect: list each as a `note`; a `blocker` only when
   something else depends on that key.
3. records: anything keyed by the name (evals/<name>/ fixtures, explorer
   data, eval-protection data, impact files) and whether the removal cleans
   it up or keeping it is intended (history is kept on purpose).
4. scope: the diff touches only the subject and its bookkeeping (for a
   skill, adam-agentskills ADR 0021 Decision 3).

Severity: `blocker` when merging would break something or leave a live
reference wrong; `note` for an expected effect or a harmless leftover.

Findings already reported by earlier rounds (report only NEW ones):
{seen}

References found by `git grep -w` for the name:
{chr(10).join(refs) if refs else 'none'}

The diff (status of every path, then the full diff of paths not deleted):
```diff
{diff}
```

Answer with one JSON object and nothing else, in a ```json fenced block:
{{"findings": [{{"severity": "blocker" | "note", "area": "references" |
"locks" | "records" | "scope" | "other", "summary": "one sentence naming the
file and what is wrong"}}]}}
An empty list means you found nothing new.
"""


def parse_answer(text: str) -> list:
    """The findings in a round's answer; anything else raises ReviewError."""
    fenced = re.findall(r"```json\s*\n(.*?)\n```", text, re.S)
    raw = fenced[-1] if fenced else text.strip()
    try:
        doc = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ReviewError("the answer is not JSON") from exc
    if not isinstance(doc, dict) or not isinstance(doc.get("findings"), list):
        raise ReviewError("the answer has no findings list")
    out = []
    for f in doc["findings"]:
        if (not isinstance(f, dict) or f.get("severity") not in SEVERITIES
                or f.get("area") not in AREAS or not isinstance(f.get("summary"), str)
                or not f["summary"].strip()):
            raise ReviewError("a finding is not in the asked shape")
        out.append({"severity": f["severity"], "area": f["area"],
                    "summary": f["summary"].strip()})
    return out


def claude_round(text: str, dirs: dict, env) -> str:
    """One fresh reviewer process; its final answer text."""
    child = {k: env[k] for k in CHILD_ENV if env.get(k)}
    child["CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC"] = "1"
    child["CLAUDE_CODE_DISABLE_AUTO_MEMORY"] = "1"
    cmd = ["claude", "-p", "--model", MODEL, "--output-format", "json",
           "--max-turns", str(MAX_TURNS), "--setting-sources", "",
           "--strict-mcp-config", "--no-session-persistence",
           "--permission-mode", "default", "--allowedTools", TOOLS]
    for path in sorted(dirs.values()):
        cmd += ["--add-dir", str(path)]
    cmd += ["--tools", TOOLS]
    with tempfile.TemporaryDirectory(prefix="skills-evals-removal-review-") as cwd:
        try:
            proc = subprocess.run(cmd, input=text, capture_output=True, text=True,
                                  timeout=ROUND_TIMEOUT, cwd=cwd, env=child)
        except subprocess.TimeoutExpired as exc:
            raise ReviewError(f"the reviewer timed out after {ROUND_TIMEOUT}s") from exc
        except OSError as exc:
            raise ReviewError(f"the reviewer could not start ({type(exc).__name__})") from exc
    if proc.returncode != 0:
        raise ReviewError(f"the reviewer exited {proc.returncode}")
    try:
        out = json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        raise ReviewError("the reviewer printed no JSON result") from exc
    if isinstance(out, list):
        out = next((e for e in out if isinstance(e, dict) and e.get("type") == "result"), {})
    if not isinstance(out, dict) or out.get("is_error") or not isinstance(out.get("result"), str):
        raise ReviewError("the reviewer reported an error")
    return out["result"]


def _key(f: dict) -> str:
    return re.sub(r"\W+", " ", f["summary"].lower()).strip()


def run_rounds(make_prompt, run_round) -> dict:
    """The stop rule. `make_prompt(prior)` builds a round's text and
    `run_round(text)` answers it. Returns {"outcome", "rounds", "findings",
    "why"}."""
    findings, rounds, worst, quiet = [], [], 0, 0
    for n in range(1, MAX_ROUNDS + 1):
        try:
            got = parse_answer(run_round(make_prompt(list(findings))))
        except ReviewError as exc:
            rounds.append({"round": n, "new": 0, "error": str(exc)})
            return {"outcome": "block", "rounds": rounds, "findings": findings,
                    "why": f"round {n} failed: {exc}"}
        seen = {_key(f) for f in findings}
        new = [f for f in got if _key(f) not in seen]
        findings += new
        rounds.append({"round": n, "new": len(new)})
        if any(f["severity"] == "blocker" for f in new):
            return {"outcome": "block", "rounds": rounds, "findings": findings,
                    "why": f"round {n} found a blocker"}
        quiet = 0 if any(SEVERITIES[f["severity"]] >= worst for f in new) else quiet + 1
        worst = max([worst, *(SEVERITIES[f["severity"]] for f in new)])
        if quiet >= QUIET_ROUNDS:
            return {"outcome": "pass", "rounds": rounds, "findings": findings,
                    "why": f"{QUIET_ROUNDS} consecutive rounds found nothing new"}
    return {"outcome": "block", "rounds": rounds, "findings": findings,
            "why": f"{MAX_ROUNDS} rounds kept finding new things"}


def review(subject: dict, checkout: Path, base: str, verdict: str, dirs: dict,
           run_round) -> dict:
    """The whole review of the removal `base..HEAD` in `checkout`."""
    scope = scope_findings(changed_paths(checkout, base), subject["target"],
                           subject["path"], subject.get("plugin"))
    if scope:
        return {"outcome": "block", "rounds": [], "findings": scope,
                "why": "the diff leaves its scope; no reviewer was started"}
    diff = diff_text(checkout, base)
    terms = [subject["name"],
             *([f"{subject['plugin']}/{subject['name']}"] if subject.get("plugin") else []),
             *([subject["heading"]] if subject.get("heading") else [])]
    refs = references(dirs, terms)
    return run_rounds(lambda prior: prompt(subject, verdict, diff, refs, dirs, prior),
                      run_round)


def _safe(text: str) -> str:
    one = " ".join(text.split())
    if len(one) > SUMMARY_LIMIT:
        one = one[:SUMMARY_LIMIT] + "…"
    return html.escape(one).replace("@", "&#64;")


def section(result: dict, run_url: str) -> str:
    """The `## Adversarial review` section, ending in the one line."""
    if not LINE_RE.fullmatch(f"{LINE_PREFIX} pass {run_url}"):
        raise ReviewError("the review needs the workflow run's URL")
    rounds = len(result["rounds"])
    lines = [HEADING, "",
             f"A fresh-context agent reviewer ({MODEL}, read-only tools) checked this "
             "removal's downstream effects: references elsewhere, consumer lock keys, "
             "records keyed by the name, and scope "
             "([skills-evals#917](https://github.com/Adam-S-Daniel/skills-evals/issues/917)). "
             f"Rounds: {rounds}. Result: **{result['outcome']}** ({_safe(result['why'])}).", ""]
    if result["findings"]:
        lines += [f"- **{f['severity']}** ({f['area']}): {_safe(f['summary'])}"
                  for f in result["findings"]]
    else:
        lines.append("- No findings.")
    lines += ["", f"{LINE_PREFIX} {result['outcome']} {run_url}"]
    return "\n".join(lines) + "\n"


def with_section(body: str, text: str) -> str:
    """`body` with the review section placed before the agent marker line
    (the body's last line), so the marker stays last."""
    head, sep, tail = body.rstrip("\n").rpartition("\n\n")
    if not sep:
        return f"{body.rstrip()}\n\n{text}"
    return f"{head}\n\n{text}\n{tail}\n"


def has_pass(body: str) -> bool:
    """Exactly one `Adversarial-review:` line in the body, and it is a pass."""
    lines = [ln for ln in body.splitlines() if ln.startswith(LINE_PREFIX)]
    return len(lines) == 1 and bool(LINE_RE.fullmatch(lines[0])) \
        and LINE_RE.fullmatch(lines[0]).group(1) == "pass"
