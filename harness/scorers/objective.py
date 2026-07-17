"""Objective (scriptable) checks against an eval output workspace.

Each check type inspects the workspace files a fixture points at and returns
(passed: bool, detail: str). Check types are registered in CHECKS; fixtures
reference them by their `type` field.
"""

from __future__ import annotations

import glob
import os
import re
import subprocess

# Remote action ref: owner/repo[/path]@ref — excludes local (./) and docker:// refs.
USES_RE = re.compile(r"^\s*-?\s*uses:\s*([^\s#]+)(\s*#.*)?\s*$")
SHA_RE = re.compile(r"^[0-9a-f]{40}$")
# Version claim inside a pin's trailing comment, e.g. "# v4.3.1 (2025-01-01)".
VERSION_COMMENT_RE = re.compile(r"#\s*(v?\d+(?:\.\d+)*)")


def _workflow_uses(workspace: str, patterns: list[str]) -> list[tuple[str, int, str, str]]:
    """Yield (file, lineno, ref, trailing_comment) for every `uses:` line."""
    out = []
    for pattern in patterns:
        for path in sorted(glob.glob(os.path.join(workspace, pattern))):
            with open(path, encoding="utf-8") as f:
                for lineno, line in enumerate(f, 1):
                    m = USES_RE.match(line)
                    if m:
                        out.append((os.path.relpath(path, workspace), lineno,
                                    m.group(1), (m.group(2) or "").strip()))
    return out


def _is_remote_action(ref: str) -> bool:
    return not ref.startswith(("./", "docker://"))


def uses_refs_sha_pinned(workspace: str, patterns: list[str]) -> tuple[bool, str]:
    bad = [f"{f}:{n} {ref}" for f, n, ref, _ in _workflow_uses(workspace, patterns)
           if _is_remote_action(ref)
           and not SHA_RE.match(ref.rsplit("@", 1)[-1])]
    return (not bad, "all remote refs SHA-pinned" if not bad
            else "unpinned: " + "; ".join(bad))


def pinned_refs_have_version_comment(workspace: str, patterns: list[str]) -> tuple[bool, str]:
    bad = [f"{f}:{n} {ref}" for f, n, ref, comment in _workflow_uses(workspace, patterns)
           if _is_remote_action(ref)
           and SHA_RE.match(ref.rsplit("@", 1)[-1])
           and not re.search(r"#\s*v?\d", comment)]
    return (not bad, "all pinned refs carry version comments" if not bad
            else "missing version comment: " + "; ".join(bad))


def yaml_parses(workspace: str, patterns: list[str]) -> tuple[bool, str]:
    import yaml
    bad = []
    for pattern in patterns:
        for path in sorted(glob.glob(os.path.join(workspace, pattern))):
            try:
                with open(path, encoding="utf-8") as f:
                    yaml.safe_load(f)
            except yaml.YAMLError as e:
                bad.append(f"{os.path.relpath(path, workspace)}: {e}")
    return (not bad, "all workflows parse" if not bad else "; ".join(bad))


def non_remote_refs_unchanged(workspace: str, patterns: list[str],
                              seed: str | None = None) -> tuple[bool, str]:
    """Local (./) and docker:// refs must match the seed workspace exactly."""
    if seed is None:
        return (False, "seed workspace not provided")
    def non_remote(ws):
        return sorted((f, ref) for f, _, ref, _ in _workflow_uses(ws, patterns)
                      if not _is_remote_action(ref))
    before, after = non_remote(seed), non_remote(workspace)
    return (before == after, "local/docker refs unchanged" if before == after
            else f"changed: seed={before} result={after}")


def _pinned_refs(workspace: str, patterns: list[str]) -> list[tuple[str, int, str, str, str | None]]:
    """(file, lineno, action, sha, claimed_version) for every SHA-pinned remote ref.

    `claimed_version` is the version token from the trailing comment
    (e.g. "v4.3.1" out of "# v4.3.1 (2025-01-01)"), or None if absent.
    """
    out = []
    for f, n, ref, comment in _workflow_uses(workspace, patterns):
        if not _is_remote_action(ref):
            continue
        action, _, tail = ref.rpartition("@")
        if not SHA_RE.match(tail):
            continue
        m = VERSION_COMMENT_RE.search(comment)
        out.append((f, n, action, tail, m.group(1) if m else None))
    return out


def _ls_remote_tags(repo_url: str, version: str,
                    timeout: int = 30) -> tuple[dict[str, str] | None, str | None]:
    """`git ls-remote <repo_url> refs/tags/<version>*` -> ({refname: sha}, None).

    Queries both the "v"-prefixed and bare spellings of the version so a
    "# 4.3.1" comment still finds a "v4.3.1" tag (and vice versa). Returns
    (None, error) on any invocation failure — network blip, timeout, missing
    git — so callers can count the ref as unverifiable instead of failing it.
    """
    core = version[1:] if version.startswith("v") else version
    try:
        proc = subprocess.run(
            ["git", "ls-remote", repo_url,
             f"refs/tags/v{core}*", f"refs/tags/{core}*"],
            capture_output=True, text=True, timeout=timeout,
            env={**os.environ, "GIT_TERMINAL_PROMPT": "0"},
        )
    except (subprocess.TimeoutExpired, OSError) as e:
        return None, str(e)
    if proc.returncode != 0:
        return None, proc.stderr.strip() or f"git ls-remote exit {proc.returncode}"
    refs = {}
    for line in proc.stdout.splitlines():
        sha, _, refname = line.partition("\t")
        if refname:
            refs[refname] = sha
    return refs, None


def _sha_matches_tag(sha: str, version: str, refs: dict[str, str]) -> bool:
    """True if `sha` is the claimed tag's commit.

    Accepts a match on the tag ref itself (lightweight tag: the ref IS the
    commit) or on its `^{}` peel (annotated tag: the ref is a tag object; the
    peel is the commit). Tries both "vX.Y.Z" and "X.Y.Z" tag spellings.
    """
    core = version[1:] if version.startswith("v") else version
    for tag in (f"v{core}", core):
        for refname in (f"refs/tags/{tag}", f"refs/tags/{tag}^{{}}"):
            if refs.get(refname) == sha:
                return True
    return False


def pinned_shas_match_tags(workspace: str, patterns: list[str], *,
                           allow_network: bool = False,
                           ls_remote=None) -> tuple[bool, str]:
    """Each pinned SHA must be the commit its version comment claims, per the
    action repo's real tags (`git ls-remote`).

    NETWORK-DEPENDENT — real-eval runs only. The hermetic test suite must
    never hit the network, so unless `allow_network` is set (run_eval.py
    `--net-checks`, passed by the real-eval workflow) the check is SKIPPED and
    reported as passed with an explicit "skipped" detail. Tests exercise the
    parsing/matching logic by injecting `ls_remote` (same contract as
    _ls_remote_tags) instead of enabling the network.

    Per-ref ls-remote failures count as "unverifiable" — a network blip on
    one ref can't flap the result while others verify. But if NOTHING could
    be verified (0 verified, 0 mismatched, >=1 unverifiable) the check fails:
    an all-unverifiable pass would let total network degradation masquerade
    as a green result. A genuine mismatch (or a claimed tag that doesn't
    exist upstream) always fails.
    """
    pinned = _pinned_refs(workspace, patterns)
    if not pinned:
        return (True, "no SHA-pinned remote refs to verify")
    if not allow_network and ls_remote is None:
        return (True, f"skipped: network checks disabled; "
                      f"{len(pinned)} pinned ref(s) unverified")
    fetch = ls_remote or _ls_remote_tags

    verified, mismatched, unverifiable = 0, [], []
    for f, n, action, sha, version in pinned:
        where = f"{f}:{n} {action}@{sha[:12]}"
        if version is None:
            # pinned_refs_have_version_comment already fails this case;
            # here there is simply no claim to verify.
            unverifiable.append(f"{where} (no version comment)")
            continue
        repo_url = "https://github.com/" + "/".join(action.split("/")[:2])
        refs, err = fetch(repo_url, version)
        if refs is None:
            unverifiable.append(f"{where} (ls-remote failed: {err})")
        elif _sha_matches_tag(sha, version, refs):
            verified += 1
        else:
            mismatched.append(f"{where} != tag {version}"
                              if refs else f"{where}: tag {version} not found upstream")

    detail = (f"{verified} verified, {len(mismatched)} mismatched, "
              f"{len(unverifiable)} unverifiable")
    all_unverifiable = not verified and not mismatched and unverifiable
    if all_unverifiable:
        detail += " — network degraded"
    if mismatched:
        detail += "; mismatched: " + "; ".join(mismatched)
    if unverifiable:
        detail += "; unverifiable: " + "; ".join(unverifiable)
    return (not mismatched and not all_unverifiable, detail)


CHECKS = {
    "uses_refs_sha_pinned": uses_refs_sha_pinned,
    "pinned_refs_have_version_comment": pinned_refs_have_version_comment,
    "yaml_parses": yaml_parses,
    "non_remote_refs_unchanged": non_remote_refs_unchanged,
    "pinned_shas_match_tags": pinned_shas_match_tags,
}


def run_checks(fixture: dict, workspace: str, seed: str, *,
               allow_network: bool = False) -> list[dict]:
    """Run every objective check in the fixture; return result dicts.

    `allow_network` opts network-dependent checks in (real-eval runs); the
    default keeps every caller — most importantly the hermetic tests — offline.
    """
    results = []
    for check in fixture.get("objective_checks", []):
        fn = CHECKS.get(check["type"])
        if fn is None:
            results.append({"id": check["id"], "passed": False,
                            "detail": f"unknown check type {check['type']!r}"})
            continue
        kwargs = {}
        if check["type"] == "non_remote_refs_unchanged":
            kwargs["seed"] = seed
        elif check["type"] == "pinned_shas_match_tags":
            kwargs["allow_network"] = allow_network
        passed, detail = fn(workspace, check.get("paths", []), **kwargs)
        results.append({"id": check["id"], "passed": passed, "detail": detail})
    return results
