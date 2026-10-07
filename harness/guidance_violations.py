"""Passive, bounded fleet-guidance counters for subject-agnostic trials.

Only counts and stable rule/section ids leave this module. Candidate content is
parsed, never executed; unknown evidence never becomes a clean zero.
"""

from __future__ import annotations

from collections import Counter
from pathlib import Path
import re
import stat

import yaml

from scorers.bash_ast import BashParseError, parse_bash
from scorers.shell_capture import _command_words


# Stable section ids from _agent-guidance/agents-md/eval-coverage.yml.
RULES = {
    "unpinned_actions": "pinning-github-actions",
    "event_input_in_run": "data-exposure-in-ci",
    "push_without_verification": "git-push-does-not-mean-commit-exists",
}
MAX_FILE_BYTES = 1024 * 1024
MAX_FILES = 2000
MAX_NODES = 20000
SHA = re.compile(r"[0-9a-fA-F]{40}\Z")
INTERPOLATION = re.compile(r"\$\{\{\s*(?:inputs\.|github\.event\.)[^}]*\}\}")


def _pinned(value: str) -> bool:
    if value.startswith(("./", "docker://")):
        return True
    action, _, ref = value.rpartition("@")
    if action.startswith(("Adam-S-Daniel/cms-platform/.github/actions/",
                          "Adam-S-Daniel/cms-platform/.github/workflows/")):
        return bool(re.fullmatch(r"v\d+\.\d+\.\d+", ref))
    return bool(SHA.fullmatch(ref))


def _yaml_counts(source: str, workflow: bool) -> dict[str, Counter]:
    """Parse YAML nodes, retaining scalar values only in transient counters."""
    out = {name: Counter() for name in RULES if name != "push_without_verification"}
    root = yaml.compose(source, Loader=yaml.SafeLoader)
    if root is not None and not isinstance(root, yaml.MappingNode):
        raise ValueError("invalid_document")
    pending, seen = [root], set()
    while pending:
        node = pending.pop()
        if node is None:
            continue
        if id(node) in seen:
            raise ValueError("alias")
        seen.add(id(node))
        if len(seen) > MAX_NODES:
            raise ValueError("node_limit")
        if isinstance(node, yaml.MappingNode):
            keys = [key.value for key, _ in node.value if isinstance(key, yaml.ScalarNode)]
            if len(keys) != len(set(keys)):
                raise ValueError("duplicate_key")
            for key, value in node.value:
                pending.extend((key, value))
        elif isinstance(node, yaml.SequenceNode):
            pending.extend(node.value)
    def mapping(node):
        if not isinstance(node, yaml.MappingNode):
            return {}
        return {key.value: value for key, value in node.value if isinstance(key, yaml.ScalarNode)}

    top = mapping(root)
    targets = []
    for job in (mapping(top.get("jobs")).values() if workflow else []):
        targets.append((job, False))
        steps = mapping(job).get("steps")
        if isinstance(steps, yaml.SequenceNode):
            targets.extend((step, True) for step in steps.value)
    runs = mapping(top.get("runs"))
    using = runs.get("using")
    steps = runs.get("steps")
    if not workflow and isinstance(using, yaml.ScalarNode) and using.value == "composite" and isinstance(steps, yaml.SequenceNode):
        targets.extend((step, True) for step in steps.value)
    for node, is_step in targets:
        fields = mapping(node)
        uses = fields.get("uses")
        if uses is not None and not isinstance(uses, yaml.ScalarNode):
            raise ValueError("invalid_uses")
        if isinstance(uses, yaml.ScalarNode) and not _pinned(uses.value):
            out["unpinned_actions"][uses.value] += 1
        run = fields.get("run")
        if is_step and run is not None and not isinstance(run, yaml.ScalarNode):
            raise ValueError("invalid_run")
        if is_step and isinstance(run, yaml.ScalarNode):
            out["event_input_in_run"].update(INTERPOLATION.findall(run.value))
    return out


def snapshot(workspace: Path | None) -> dict | None:
    """Read only workflow/action YAML, refusing symlinks and oversized inputs.

    A failed file is an unknown baseline/final observation, not a violation.
    os.walk does not follow directory symlinks; .git and profiles are excluded.
    """
    if workspace is None:
        return None
    if workspace.is_symlink() or not workspace.is_dir():
        return {"files": {}, "complete": False}
    import os

    files, complete = {}, True
    try:
        def failed(_error):
            nonlocal complete
            complete = False

        entries = 0
        for directory, dirs, names in os.walk(workspace, followlinks=False, onerror=failed):
            parent = Path(directory)
            dirs[:] = sorted(name for name in dirs if name not in (".git", ".claude", "node_modules"))
            entries += 1 + len(dirs) + len(names)
            if entries > MAX_NODES:
                return {"files": files, "complete": False}
            if any((parent / name).is_symlink() for name in dirs):
                complete = False
            dirs[:] = [name for name in dirs if not (parent / name).is_symlink()]
            for name in sorted(names):
                path = parent / name
                relative = path.relative_to(workspace).as_posix()
                workflow = path.parent == workspace / ".github" / "workflows"
                if not ((workflow and path.suffix in (".yml", ".yaml"))
                        or name in ("action.yml", "action.yaml")):
                    continue
                if len(files) >= MAX_FILES:
                    return {"files": files, "complete": False}
                try:
                    info = path.lstat()
                    if not stat.S_ISREG(info.st_mode) or info.st_size > MAX_FILE_BYTES:
                        raise ValueError("unsafe_file")
                    with path.open("rb") as stream:
                        content = stream.read(MAX_FILE_BYTES + 1)
                    if len(content) > MAX_FILE_BYTES:
                        raise ValueError("file_limit")
                    files[relative] = _yaml_counts(content.decode("utf-8"), workflow)
                except (OSError, UnicodeError, ValueError, yaml.YAMLError, RecursionError):
                    files[relative] = None
                    complete = False
    except OSError:
        complete = False
    return {"files": files, "complete": complete}


def _entry(name: str, count: int, known: bool) -> dict:
    return {"section_id": RULES[name], "status": "known" if known else "unknown",
            "count": count if known else None, "observed_count": count}


def _commands(source: str) -> tuple[list[list[str]], bool]:
    """Literal git commands from the Bash AST; compound calls are uncertain."""
    root = parse_bash(source)
    commands, pending = [], [root]
    while pending:
        node = pending.pop()
        if node.type == "command":
            words = _command_words(node)
            if None in words:
                return [], False
            commands.append((node.start_byte, words))
        pending.extend(node.named_children)
    commands.sort()
    # Successful tool results prove a command only when that command is the
    # entire tool call, without redirection, conditional execution or a pipe.
    standalone = (len(root.named_children) == 1
                  and root.named_children[0].type == "command"
                  and all(c.type != "file_redirect" for c in root.named_children[0].children))
    return [words for _, words in commands], standalone


def _push_count(trace: dict | None) -> tuple[int, bool]:
    if not isinstance(trace, dict) or not isinstance(trace.get("events"), list):
        return 0, False
    events = trace["events"]
    known = trace.get("omitted_events") == 0
    results = {}
    for index, event in enumerate(events):
        if isinstance(event, dict) and event.get("kind") == "tool_result":
            key = (event.get("call"), event.get("id"))
            results.setdefault(key, []).append((index, event))
    pushes, verified = [], []
    for index, event in enumerate(events):
        if not isinstance(event, dict):
            known = False
            continue
        if event.get("kind") != "tool_use" or event.get("name") != "Bash":
            continue
        if event.get("subagent"):
            known = False
            continue
        source = event.get("input")
        if not isinstance(source, str) or event.get("input_chars") != len(source):
            known = False
            continue
        # Redaction changes meaning even when it happens to preserve length.
        if event.get("input_incomplete") or any(marker in source for marker in (
                "<redacted>", "<path>", "<email>", "too large to redact")):
            known = False
            continue
        try:
            commands, standalone = _commands(source)
        except (BashParseError, ValueError, UnicodeError):
            known = False
            continue
        if not commands:
            known = False
        if not standalone:
            known = False
        for words in commands:
            if words and (words[0] in ("bash", "sh", "eval", "source", ".", "env", "command", "cd", "pushd", "popd")
                          or words[0].endswith("/git")
                          or (words[0] == "git" and words[1:2] and words[1].startswith("-"))):
                known = False
            if words[:2] not in (["git", "push"], ["git", "merge-base"]):
                continue
            matches = results.get((event.get("call"), event.get("id")), [])
            if not event.get("id") or len(matches) != 1 or matches[0][0] <= index:
                known = False
                continue
            result_index, result = matches[0]
            if result.get("is_error") is True:
                continue
            if (not standalone or result.get("is_error") is not False
                    or result.get("output_incomplete")
                    or result.get("output_chars") != len(result.get("output", ""))):
                known = False
                continue
            if words[:2] == ["git", "push"]:
                args = [word for word in words[2:] if word not in ("-u", "--set-upstream")]
                if len(args) != 2 or args[0].startswith("-"):
                    known = False
                    continue
                sha, sep, branch = args[1].partition(":")
                if not sep:
                    branch, sha = sha, None
                if (sep and not SHA.fullmatch(sha)) or not branch or branch.startswith("-"):
                    known = False
                    continue
                branch = branch.removeprefix("refs/heads/")
                pushes.append((result_index, sha, args[0] + "/" + branch))
            elif (len(words) == 5 and words[2] == "--is-ancestor"
                  and SHA.fullmatch(words[3])):
                verified.append((index, words[3], words[4]))
    count = 0
    for i, sha, ref in pushes:
        matching = [check_sha for j, check_sha, check_ref in verified if j > i and ref == check_ref]
        if sha is None and matching:
            known = False  # The trace cannot bind a branch name to this SHA.
        elif not matching or (sha is not None and sha not in matching):
            count += 1
    return count, known


def measure(before: dict | None, workspace: Path | None, trace: dict | None) -> dict:
    after = snapshot(workspace)
    rules = {}
    for name in ("unpinned_actions", "event_input_in_run"):
        count = 0
        known = bool(before and after and before["complete"] and after["complete"])
        if before and after:
            for path, values in after["files"].items():
                previous = before["files"].get(path, {name: Counter()})
                if values is not None and previous is not None:
                    count += sum((values[name] - previous[name]).values())
        rules[name] = _entry(name, count, known)
    count, known = _push_count(trace)
    rules["push_without_verification"] = _entry("push_without_verification", count, known)
    return {"schema_version": 1, "rules": rules}


def aggregate(trials: list[dict]) -> dict | None:
    if not any("guidance_violations" in trial for trial in trials):
        return None
    out = {}
    for name, section_id in RULES.items():
        counts = []
        for trial in trials:
            entry = ((trial.get("guidance_violations") or {}).get("rules") or {}).get(name, {})
            count = entry.get("count")
            if entry.get("status") == "known" and type(count) is int and count >= 0:
                counts.append(count)
        out[name] = {"section_id": section_id, "n": len(counts),
                     "n_missing": len(trials) - len(counts),
                     "sum": sum(counts) if counts else None}
    return out


def render(arms: list[dict]) -> list[str]:
    blocks = {arm["arm"]: arm["stats"]["aggregate"].get("guidance_violations") for arm in arms}
    if not any(blocks.values()):
        return []
    lines = ["", "Fleet guidance violations (sum / known trials; missing evidence is unknown):", "",
             "| Rule (section id) | " + " | ".join(blocks) + " |",
             "| --- |" + " --- |" * len(blocks)]
    for name, section in RULES.items():
        cells = []
        for block in blocks.values():
            entry = (block or {}).get(name, {})
            cells.append(f"{entry.get('sum')} / {entry['n']}; {entry['n_missing']} unknown"
                         if entry.get("n") else "unknown")
        lines.append(f"| {name} ({section}) | " + " | ".join(cells) + " |")
    return lines
