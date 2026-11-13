"""Collect workflow runs (7 days) and merge routine runs into $DASHBOARD_HOME/inputs/run_stream.json.
Repos come from config/site.json run_console_repos.
usage: python3 collect_runs.py '<json list of {trigger_id,name,fired_at,finished_at,status}>'"""
import json, subprocess, sys, datetime as dt
import os
H = os.environ.get("DASHBOARD_HOME") or sys.exit("DASHBOARD_HOME is not set: export it as the private dashboard folder (config/, inputs/, ds/, watch/) and run again.")
INP = os.path.join(H, "inputs/run_stream.json")
REPOS = json.load(open(os.path.join(H, "config/site.json"))).get("run_console_repos") or sys.exit(
    "config/site.json has no run_console_repos: list the owner/repo names whose workflow runs the run console shows.")
now = dt.datetime.now(dt.timezone.utc); since = (now - dt.timedelta(days=7)).strftime("%Y-%m-%dT%H:%M:%SZ")
try: old = json.load(open(INP))
except Exception: old = {}
wf, errs = {}, []
for r in REPOS:
    for page in range(1, 11):
        try:
            out = subprocess.run(["gh", "api", f"repos/{r}/actions/runs?per_page=100&page={page}&created=>={since}"],
                                 capture_output=True, text=True, timeout=60)
            if out.returncode: errs.append(f"{r}: exit {out.returncode}"); break
            runs = json.loads(out.stdout)["workflow_runs"]
        except Exception as e:
            errs.append(f"{r}: {type(e).__name__}"); break
        for x in runs:
            wf[x["html_url"]] = {"repo": r, "workflow": x["name"], "event": x["event"], "status": x["status"],
                                 "conclusion": x["conclusion"], "created_at": x["created_at"], "updated_at": x["updated_at"],
                                 "html_url": x["html_url"], "display_title": x["display_title"]}
        if len(runs) < 100: break
# keep earlier-collected runs for repos that failed this pass
for x in old.get("workflow_runs", []):
    if x["html_url"] not in wf and x["created_at"] >= since and any(e.startswith(x["repo"] + ":") for e in errs):
        wf[x["html_url"]] = x
rr = {f'{x["trigger_id"]}@{x["fired_at"]}': x for x in old.get("routine_runs", []) if x["fired_at"] >= since}
for x in json.loads(sys.argv[1] if len(sys.argv) > 1 else "[]"):
    rr[f'{x["trigger_id"]}@{x["fired_at"]}'] = x
json.dump({"collected_at": now.strftime("%Y-%m-%dT%H:%M:%SZ"), "errors": errs,
           "workflow_runs": sorted(wf.values(), key=lambda x: x["created_at"], reverse=True),
           "routine_runs": sorted(rr.values(), key=lambda x: x["fired_at"], reverse=True)}, open(INP, "w"), indent=1)
bad = [x for x in wf.values() if x["conclusion"] in ("failure", "timed_out", "startup_failure")]
print(f"workflow runs {len(wf)}, routine runs {len(rr)}, errors {errs}, failures {len(bad)}")
