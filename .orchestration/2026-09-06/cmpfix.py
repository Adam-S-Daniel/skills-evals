import json, subprocess, sys
tree, fx = sys.argv[1], sys.argv[2]
p = subprocess.run([sys.executable, "harness/run_eval.py", fx, "--arm", "objective-only"], cwd=tree, capture_output=True, text=True)
out = p.stdout.strip()
def walk(o, acc):
    if isinstance(o, dict):
        if "id" in o and "passed" in o and isinstance(o["passed"], bool):
            acc.append("%s=%s" % (o["id"], o["passed"]))
        for v in o.values(): walk(v, acc)
    elif isinstance(o, list):
        for v in o: walk(v, acc)
try:
    o = json.loads(out); cells = []; walk(o, cells)
    err = o.get("error") or ""
    print("exit=%d %s%s" % (p.returncode, ",".join(cells) or "NOCHECKS", (" error=" + str(err)[:200]) if err else ""))
except Exception:
    print("exit=%d NOJSON stderr=%s" % (p.returncode, (p.stderr.strip().splitlines() or [""])[-1][:200]))
