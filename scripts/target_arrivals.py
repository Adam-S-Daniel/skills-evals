#!/usr/bin/env python3
"""How many targets (git hooks, skills, guidance sections) were added and
removed each ISO week, counted from each source repository's git history, and
how many of the added ones are eval-eligible now. Adam, 2026-11-15: the
arrival rate the catch-up forecast uses must come from data, never a hand
count.

    target_arrivals.py repos --config evals/target-sources.yml
        One line per repository to clone, `owner/name<TAB>public|private`.
    target_arrivals.py build --config evals/target-sources.yml
        --checkouts DIR --as-of TIME [--usage usage/weekly-local.json]
        --out arrivals.json

`build` reads DIR/<owner>__<name>, a full-history (never shallow) clone of
each repository; `--filter=blob:none` is enough, and only a private
registry's trees are read (no blob of a private repository). target-arrivals.yml
publishes the result as `arrivals/targets.json` on persistent/eval-results,
and scripts/forecast_catch_up.py `--arrivals` reads it.

THE SOURCES. evals/target-sources.yml lists the git hook and guidance
sources; skills come from every registry in harness/registries.yml (its
`layout` glob and `private` flag). A version is the set of target names at a
first-parent commit of the default branch that touched the source's path.
A source's first version is its BASELINE: what it held when it began, never
counted as additions. A name that appears is an addition at that commit's
time; one that disappears is a removal. A rename reads as one of each.

ELIGIBILITY (of each addition, judged as of `--as-of`):
  * skill: eligible once it has a recorded use in real work
    (`skill_usage.has_recorded_use`, the eval scope pass's own question, on
    the surfaces it reaches) or is listed in evals/usage-unknown.yml (its
    evals are never paused for use). A skill since removed is not eligible.
    Unknown (stale census, an untracked name) stays null, never false.
  * guidance-section: eligible while its eval-coverage.yml row is not
    `skipped`; a removed row is not eligible.
  * git-hook: null. Hook verdicts come from use, not eval runs.

THE RATES. Per kind, over the `rate_weeks` weeks ending at `--as-of`,
cut to start no earlier than the newest baseline among
that kind's sources (a source cannot add what it did not yet track):
additions and removals per week, and the eligible share of the additions
whose eligibility is known. A kind with an unreadable source (no checkout, a
shallow one, a version or blob it cannot read) has `complete: false` and
null rates: an undercount is not a rate. A complete kind whose cut window
is under a week also has null rates (too short to be a rate); a reader
takes a null rate as unknown either way.

PUBLIC BY CONSTRUCTION. The document goes on a public branch. A target's
name is written only for a source whose repository is public (a registry
with `private: false`, or a config source not marked `private: true`); a
private source's additions are counted with `name: null`. No path, message
or author from any history is written.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "harness"))
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import timeweeks  # noqa: E402

SCHEMA = 1
KINDS = ("git-hook", "skill", "guidance-section")
CONFIG_KINDS = ("git-hook", "guidance-section")
PARSERS = {"git-hook": ("agent-checks", "repo-local"), "guidance-section": ("eval-coverage",)}
REGISTRIES = REPO_ROOT / "harness" / "registries.yml"
REPO_RE = re.compile(r"[A-Za-z0-9-]{1,39}/[A-Za-z0-9._-]{1,100}")
PATH_RE = re.compile(r"[A-Za-z0-9._*-]+(?:/[A-Za-z0-9._*-]+)*")
SHA_RE = re.compile(r"[0-9a-f]{40}")
#: The layout of adam-agentskills, whose plugin_layout.json says which
#: plugins are local-only (eval_scope's surfaces).
LAYOUT_REPO = "Adam-S-Daniel/adam-agentskills"
LAYOUT_FILE = "scripts/plugin_layout.json"


class ArrivalsError(Exception):
    """A config or registry file that cannot be used. Fixed text."""


class Unreadable(Exception):
    """One source's history cannot be read. Fixed text, never git output."""


# --- sources ----------------------------------------------------------------------

def _yaml(path: Path):
    try:
        return yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, yaml.YAMLError) as exc:
        raise ArrivalsError(f"{Path(path).name} is unreadable") from exc


def load_sources(config: Path, registries: Path = REGISTRIES) -> tuple[int, list]:
    """(rate_weeks, sources): the config's sources, checked, then one
    `skill-dirs` source per registry in `registries`."""
    doc = _yaml(config)
    if not isinstance(doc, dict) or set(doc) != {"rate_weeks", "sources"}:
        raise ArrivalsError("the config needs exactly rate_weeks and sources")
    weeks = doc["rate_weeks"]
    if type(weeks) is not int or weeks < 1:
        raise ArrivalsError("rate_weeks must be a whole number of weeks, at least 1")
    if not isinstance(doc["sources"], list):
        raise ArrivalsError("sources must be a list")
    out = []
    for row in doc["sources"]:
        if not isinstance(row, dict) or not {"kind", "repo", "path", "parser"} <= set(row) \
                or not set(row) <= {"kind", "repo", "path", "parser", "private"}:
            raise ArrivalsError("each source needs kind, repo, path and parser (and may set private)")
        kind, repo, path, parser = row["kind"], row["repo"], row["path"], row["parser"]
        if kind not in CONFIG_KINDS or parser not in PARSERS[kind]:
            raise ArrivalsError("a source has an unknown kind or a parser its kind does not take")
        if not isinstance(repo, str) or not REPO_RE.fullmatch(repo) \
                or not isinstance(path, str) or not PATH_RE.fullmatch(path) or "*" in path:
            raise ArrivalsError("a source has a malformed repo or path")
        private = row.get("private", False)
        if type(private) is not bool:
            raise ArrivalsError("private must be true or false")
        out.append({"kind": kind, "repo": repo, "path": path, "parser": parser,
                    "private": private})
    reg = _yaml(registries)
    rows = reg.get("registries") if isinstance(reg, dict) else None
    if not isinstance(rows, list) or not rows:
        raise ArrivalsError("harness/registries.yml lists no registries")
    for row in rows:
        url, layout = (row or {}).get("url"), (row or {}).get("layout")
        repo = url.removeprefix("https://github.com/") if isinstance(url, str) else None
        if not repo or not REPO_RE.fullmatch(repo) or not isinstance(layout, str) \
                or not PATH_RE.fullmatch(layout) or not layout.endswith("/*/SKILL.md") \
                or type(row.get("private")) is not bool:
            raise ArrivalsError("a registry needs a GitHub url, a */SKILL.md layout and private")
        out.append({"kind": "skill", "repo": repo, "path": layout, "parser": "skill-dirs",
                    "private": row["private"]})
    # A repository is private for every source if any source says so, so a
    # config row that forgets `private: true` cannot publish its names.
    private = {repo for repo, flag in repos(out) if flag}
    for source in out:
        source["private"] = source["repo"] in private
    return weeks, out


def repos(sources: list) -> list:
    """[(owner/name, private)] to clone, each once; private if any source of
    it says so."""
    seen: dict = {}
    for s in sources:
        seen[s["repo"]] = seen.get(s["repo"], False) or s["private"]
    return sorted(seen.items())


def checkout_dir(root: Path, repo: str) -> Path:
    return Path(root) / repo.replace("/", "__")


# --- history ----------------------------------------------------------------------

def _git(root: Path, *args: str) -> str:
    return subprocess.run(["git", "-C", str(root), *args], check=True, capture_output=True,
                          text=True, encoding="utf-8").stdout


def _layout_re(layout: str) -> re.Pattern:
    return re.compile("/".join("[^/]+" if part == "*" else re.escape(part)
                               for part in layout.split("/")))


def _pathspec(source: dict) -> str:
    """The fixed prefix of a layout glob, or the path itself."""
    if source["parser"] != "skill-dirs":
        return source["path"]
    fixed = []
    for part in source["path"].split("/"):
        if "*" in part:
            break
        fixed.append(part)
    return "/".join(fixed) or "."


def names_at(root: Path, sha: str, source: dict) -> frozenset:
    """The target names `source` holds at commit `sha`. Raises Unreadable."""
    parser, path = source["parser"], source["path"]
    try:
        if parser == "skill-dirs":
            pattern = _layout_re(path)
            # Trees only (no blob fetch from a partial clone); -z so a
            # non-ASCII directory name is not quoted out of the match.
            listing = _git(root, "ls-tree", "-r", "-z", "--name-only", sha, "--",
                           _pathspec(source))
            return frozenset(name.split("/")[-2] for name in listing.split("\0")
                             if pattern.fullmatch(name))
        # Presence from the tree, never from a blob read: in a partial clone
        # a failed blob fetch must not read as a deleted file.
        present = _git(root, "ls-tree", "-z", "--name-only", sha, "--", path)
        if path not in present.split("\0"):
            return frozenset()
        if parser == "repo-local":
            return frozenset({f"repo-local:{source['repo']}"})
        text = _git(root, "show", f"{sha}:{path}")
    except (OSError, subprocess.CalledProcessError, UnicodeDecodeError) as exc:
        raise Unreadable from exc
    if parser == "agent-checks":
        import explorer_public  # noqa: PLC0415 - the Tree-sitter parse
        ids = explorer_public.fleet_check_ids(text.encode("utf-8"))
        if ids is None:
            raise Unreadable
        return frozenset(ids)
    return frozenset(coverage_rows(text))  # eval-coverage


def coverage_rows(text: str) -> dict:
    """{row id: status} of an agents-md/eval-coverage.yml. Raises Unreadable."""
    try:
        doc = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        raise Unreadable from exc
    if not isinstance(doc, list) or not all(isinstance(r, dict) and "id" in r for r in doc):
        raise Unreadable
    return {str(r["id"]): r.get("status") for r in doc}


def versions(root: Path, source: dict, as_of: datetime) -> list:
    """[(commit time, names)] of every first-parent commit at or before
    `as_of` touching the source's path, oldest first. Raises Unreadable on
    a missing or shallow checkout or no such commit."""
    try:
        if not (Path(root) / ".git").exists() \
                or _git(root, "rev-parse", "--is-shallow-repository").strip() != "false":
            raise Unreadable
        log = _git(root, "log", "--first-parent", "--reverse", "--format=%H %cI", "HEAD", "--",
                   _pathspec(source))
    except (OSError, subprocess.CalledProcessError) as exc:
        raise Unreadable from exc
    # History order, never sorted by date: a committer clock that ran
    # backwards must not swap two versions.
    out = []
    for line in log.splitlines():
        sha, _, stamp = line.partition(" ")
        when = timeweeks.parse_ts(stamp)
        if not SHA_RE.fullmatch(sha) or when is None:
            raise Unreadable
        if when <= as_of:
            out.append((when.astimezone(timezone.utc), names_at(root, sha, source)))
    if source["parser"] == "repo-local":
        # A repository holds no local checks until its file appears, so its
        # baseline is empty at its first commit and the file's creation is an
        # addition. One that never had the file holds none.
        try:
            first = _git(root, "log", "--first-parent", "--max-parents=0", "--format=%cI", "HEAD")
        except (OSError, subprocess.CalledProcessError) as exc:
            raise Unreadable from exc
        starts = [t for t in map(timeweeks.parse_ts, first.split()) if t is not None]
        if not starts:
            raise Unreadable
        out.insert(0, (min(starts).astimezone(timezone.utc), frozenset()))
    if not out:
        raise Unreadable
    return out


def changes(history: list) -> list:
    """[(time, added names, removed names)] between consecutive versions;
    the first version is the baseline."""
    out = []
    for (_, before), (when, after) in zip(history, history[1:]):
        if after != before:
            out.append((when, after - before, before - after))
    return out


# --- eligibility ------------------------------------------------------------------

def skill_eligibility(names_now: dict, usage_doc, now: datetime, plugins: dict,
                      exempt) -> callable:
    """A function (repo, name) -> True/False/None for a skill addition;
    `names_now` maps (repo, kind) to the names its sources hold now."""
    import eval_scope  # noqa: PLC0415
    import skill_usage  # noqa: PLC0415

    def judge(repo: str, name: str):
        if name not in names_now.get((repo, "skill"), frozenset()):
            return False
        if name in exempt:
            return True
        return skill_usage.has_recorded_use(usage_doc, name, now,
                                            surfaces=eval_scope._surfaces(name, plugins))
    return judge


def plugin_map(root: Path) -> dict:
    """{skill: plugin} from adam-agentskills' plugin_layout.json at HEAD; {}
    when unreadable (every skill then reads as reaching both surfaces)."""
    try:
        doc = json.loads(_git(root, "show", f"HEAD:{LAYOUT_FILE}"))
    except (OSError, subprocess.CalledProcessError, ValueError):
        return {}
    out = {}
    for plugin, body in (doc.get("plugins") or {}).items() if isinstance(doc, dict) else ():
        for skill in (body or {}).get("skills") or []:
            out[str(skill)] = plugin
    return out


# --- the document -----------------------------------------------------------------

def monday(moment: datetime) -> datetime:
    day = moment.astimezone(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    return day - timedelta(days=day.weekday())


def _iso(moment: datetime) -> str:
    return moment.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def build(sources: list, rate_weeks: int, checkouts: Path, as_of: datetime,
          usage_doc=None, exempt=frozenset()) -> dict:
    """The arrivals document (module docstring)."""
    histories, status = {}, []
    for i, s in enumerate(sources):
        root = checkout_dir(checkouts, s["repo"])
        try:
            histories[i] = versions(root, s, as_of)
            status.append(None)
        except Unreadable:
            status.append("unreadable")
    names_now = {}
    sections_now = {}
    for i, s in enumerate(sources):
        if i in histories:
            key = (s["repo"], s["kind"])
            names_now[key] = names_now.get(key, frozenset()) | histories[i][-1][1]
            if s["parser"] == "eval-coverage":
                try:
                    sections_now.update(coverage_rows(_git(
                        checkout_dir(checkouts, s["repo"]), "show", f"HEAD:{s['path']}")))
                except (OSError, subprocess.CalledProcessError, Unreadable):
                    status[i] = "unreadable"
                    del histories[i]
    layout_root = checkout_dir(checkouts, LAYOUT_REPO)
    judge_skill = skill_eligibility(names_now, usage_doc, as_of, plugin_map(layout_root), exempt)

    items = []
    for i, s in enumerate(sources):
        if i not in histories:
            continue
        for when, added, removed in changes(histories[i]):
            for event, names in (("added", added), ("removed", removed)):
                for name in sorted(names):
                    eligible = None
                    if event == "added" and s["kind"] == "skill":
                        eligible = judge_skill(s["repo"], name)
                    elif event == "added" and s["kind"] == "guidance-section":
                        state = sections_now.get(name)
                        eligible = state is not None and state != "skipped"
                    items.append({"kind": s["kind"], "event": event, "at": _iso(when),
                                  "week": monday(when).date().isoformat(),
                                  "repo": None if s["private"] else s["repo"],
                                  "name": None if s["private"] else name,
                                  "eligible": eligible})
    items.sort(key=lambda r: (r["at"], r["kind"], r["event"], r["name"] or ""))

    end = as_of
    rates = {}
    for kind in KINDS:
        own = [i for i, s in enumerate(sources) if s["kind"] == kind]
        complete = bool(own) and all(i in histories for i in own)
        start = end - timedelta(weeks=rate_weeks)
        if complete:
            start = max([start] + [histories[i][0][0] for i in own])
        weeks = (end - start) / timedelta(weeks=1)
        entry = {"complete": complete, "from": _iso(start), "to": _iso(end),
                 "weeks": round(weeks, 4) if weeks > 0 else 0,
                 "added_per_week": None, "removed_per_week": None,
                 "added": None, "removed": None, "eligible_share": None}
        if complete and weeks >= 1:
            window = [r for r in items if r["kind"] == kind
                      and start <= timeweeks.parse_ts(r["at"]) < end]
            added = [r for r in window if r["event"] == "added"]
            removed = [r for r in window if r["event"] == "removed"]
            known = [r["eligible"] for r in added if r["eligible"] is not None]
            entry.update({"added": len(added), "removed": len(removed),
                          "added_per_week": len(added) / weeks,
                          "removed_per_week": len(removed) / weeks,
                          "eligible_share": (sum(known) / len(known)) if known else None})
        rates[kind] = entry

    weekly: dict = {}
    for r in items:
        row = weekly.setdefault((r["week"], r["kind"]), {
            "week": r["week"], "kind": r["kind"], "added": 0, "removed": 0,
            "added_eligible": 0, "added_eligibility_unknown": 0})
        row[r["event"]] += 1
        if r["event"] == "added":
            if r["eligible"] is True:
                row["added_eligible"] += 1
            elif r["eligible"] is None:
                row["added_eligibility_unknown"] += 1

    return {
        "schema": SCHEMA,
        "as_of": _iso(as_of),
        "rate_weeks": rate_weeks,
        "kinds": list(KINDS),
        "sources": [{"kind": s["kind"], "repo": None if s["private"] else s["repo"],
                     "parser": s["parser"], "private": s["private"],
                     "status": status[i] or "ok",
                     "since": _iso(histories[i][0][0]) if i in histories else None,
                     "current": len(histories[i][-1][1]) if i in histories else None}
                    for i, s in enumerate(sources)],
        "rates": rates,
        "weeks": [weekly[k] for k in sorted(weekly)],
        "items": items,
    }


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = p.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("repos")
    r.add_argument("--config", type=Path, required=True)
    r.add_argument("--registries", type=Path, default=REGISTRIES)
    b = sub.add_parser("build")
    b.add_argument("--config", type=Path, required=True)
    b.add_argument("--registries", type=Path, default=REGISTRIES)
    b.add_argument("--checkouts", type=Path, required=True)
    b.add_argument("--as-of", required=True)
    b.add_argument("--usage", type=Path, default=None)
    b.add_argument("--out", type=Path, required=True)
    args = p.parse_args(argv)
    try:
        rate_weeks, sources = load_sources(args.config, args.registries)
    except ArrivalsError as exc:
        print(f"target_arrivals: {exc}", file=sys.stderr)
        return 2
    if args.cmd == "repos":
        for repo, private in repos(sources):
            print(f"{repo}\t{'private' if private else 'public'}")
        return 0
    as_of = timeweeks.parse_ts(args.as_of)
    if as_of is None:
        print("target_arrivals: --as-of is not an RFC 3339 time", file=sys.stderr)
        return 2
    import eval_scope  # noqa: PLC0415
    import skill_usage  # noqa: PLC0415
    usage_doc = skill_usage.load(args.usage) if args.usage else None
    try:
        exempt = frozenset(eval_scope.usage_unknown(REPO_ROOT))
    except eval_scope.ScopeError:
        print("target_arrivals: evals/usage-unknown.yml is malformed", file=sys.stderr)
        return 2
    doc = build(sources, rate_weeks, args.checkouts, as_of, usage_doc, exempt)
    doc["generated_at"] = _iso(datetime.now(timezone.utc))
    args.out.write_text(json.dumps(doc, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    for kind in KINDS:
        rate = doc["rates"][kind]
        print(f"{kind}: complete={rate['complete']} added={rate['added']} "
              f"removed={rate['removed']} over {rate['weeks']} weeks")
    return 0


if __name__ == "__main__":
    sys.exit(main())
