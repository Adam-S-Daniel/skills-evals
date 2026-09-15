"""Driver: run harness/roster.py's real CLI with files on disk, against any tree."""
import json, os, subprocess, sys, tempfile, shutil
from datetime import datetime, timedelta, timezone
from pathlib import Path

def iso_week(m):
    y, w, _ = m.isocalendar()
    return f"{y}-W{w:02d}"

def weeks_back(n, now=None):
    now = now or datetime.now(timezone.utc)
    return [iso_week(now - timedelta(weeks=i)) for i in range(n)]

def model(mid, created="2025-01-01T00:00:00Z"):
    return {"id": mid, "created_at": created}

def policy_text(tree, entry_pct=None, extra=None):
    """Read the tree's real policy, optionally overriding one scalar."""
    txt = (Path(tree) / "evals" / "roster-policy.yml").read_text(encoding="utf-8")
    if entry_pct is not None:
        txt = txt.replace("arm_enter_usage_pct: 10", f"arm_enter_usage_pct: {entry_pct}")
    if extra:
        txt += "\n" + extra + "\n"
    return txt

def run(tree, *, models, census, previous, entry_pct=None, workdir=None,
        env_extra=None, census_omit=False, keep=False):
    tmp = workdir or tempfile.mkdtemp(prefix="rost")
    d = Path(tmp); d.mkdir(parents=True, exist_ok=True)
    (d / "models.json").write_text(json.dumps(models), encoding="utf-8")
    if census is not None:
        (d / "census.json").write_text(json.dumps(census), encoding="utf-8")
    if previous is not None:
        (d / "previous.json").write_text(json.dumps(previous), encoding="utf-8")
    (d / "policy.yml").write_text(policy_text(tree, entry_pct), encoding="utf-8")
    cmd = [sys.executable, str(Path(tree) / "harness" / "roster.py"),
           "--models", str(d / "models.json"),
           "--policy", str(d / "policy.yml"),
           "--out", str(d / "out" / "latest.json")]
    if not census_omit and census is not None:
        cmd += ["--census", str(d / "census.json")]
    elif not census_omit and census is None:
        pass
    if previous is not None:
        cmd += ["--previous", str(d / "previous.json")]
    env = dict(os.environ)
    env.pop("PYTHONHASHSEED", None)
    if env_extra:
        env.update(env_extra)
    p = subprocess.run(cmd, capture_output=True, text=True, cwd=str(tree), env=env)
    out = None
    op = d / "out" / "latest.json"
    if op.exists():
        out = json.loads(op.read_text(encoding="utf-8"))
    res = {"rc": p.returncode, "stdout": p.stdout, "stderr": p.stderr,
           "roster": out, "dir": str(d)}
    if not keep and workdir is None:
        shutil.rmtree(tmp, ignore_errors=True)
    return res

def reason_for(res, mid):
    if not res["roster"]:
        return None
    for a in res["roster"]["arms"]:
        if a["id"] == mid:
            return a["reason"]
    for k in ("excluded", "unranked"):
        for a in res["roster"].get(k, []):
            if a["id"] == mid:
                return "[%s] %s" % (k, a["reason"])
    return None
