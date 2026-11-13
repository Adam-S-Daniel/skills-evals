#!/bin/bash
# usage: DASHBOARD_HOME=<private dashboard folder> refresh.sh '<json trigger updates>' '<json {thread_suffix: last_activity}>'
# Run from a skills-evals checkout detached at origin/main (dashboard/README.md "Refresh").
# This script never checks out another commit: bash reads a script as it runs.
set -e
: "${DASHBOARD_HOME:?is not set: export it as the private dashboard folder (config/, inputs/, ds/, watch/)}"
SE=$(cd "$(dirname "$0")/../.." && pwd)
cd "$DASHBOARD_HOME/inputs/"
python3 - "$1" "$2" <<'EOF'
import json,subprocess,sys
# Arg 1 must be a FULL live read of every scheduled task the routines table
# shows (list_triggers, every page, plus get_trigger for on-demand ones), one
# entry per id: {enabled, cron_expression, next_run_at, last_run}. Each row is
# replaced, never patched, and stamped read_at. A missing id stops the
# refresh: until 2026-11-12 the refresh passed only its own row, so every
# other row sat on its Nov 9 values for three days (thread "Fix routines
# table in dashboard").
import datetime,os,re
H=os.environ['DASHBOARD_HOME']
UTC=datetime.timezone.utc
nowdt=datetime.datetime.now(UTC)
def ts(x): return datetime.datetime.fromisoformat(x.replace('Z','+00:00'))
# Inputs that refresh.sh does not read itself must be fresh, or the page
# shows old answers as current (2026-11-12 UX review, C6 and C7).
age=(nowdt.timestamp()-os.path.getmtime('threads.json'))/3600
if age>1:
  sys.exit(f"STOP: inputs/threads.json is {age:.1f} hours old. Rebuild it from the FULL list_threads listing (every page) and run again.")
newest=max(x['last_activity_at'] for x in json.load(open('threads.json')))
try: through=json.load(open('owner_messages_read.json'))['read_through']
except (OSError,KeyError,ValueError): through='1970-01-01T00:00:00Z'
if (ts(newest)-ts(through)).total_seconds()>24*3600:
  sys.exit(f"STOP: the owner-message ledger was read through {through}, but threads were active until {newest}. Read the project chat and every thread active since {through} (list_threads since), pass the owner's messages to dashboard/refresh/append_owner_messages.py --read-through <time you started reading>, and run again.")
# A scheduled fire that never arrives leaves no trace of its own; say so here.
runs=re.findall(r'^- (\d{4}-\d\d-\d\dT\d\d:\d\dZ) (?:- )?(?:\S+Z )?refresh', open(H+'/watch/log.md').read(), re.M)
if runs and (nowdt-ts(runs[-1].replace('Z',':00Z'))).total_seconds()>13*3600:
  print(f"MISSED: the last refresh logged was {runs[-1]}, over 13 hours ago; at least one scheduled run never happened. Say so in this run's log.md line.")
cfg=json.load(open(H+'/config/routines.json'))
site=json.load(open(H+'/config/site.json'))
want=[r['source']['id'] for r in cfg if r.get('source',{}).get('kind')=='trigger' and not r.get('retired')]
live=json.loads(sys.argv[1])
missing=[i for i in want if i not in live]
if missing:
  sys.exit("STOP: arg 1 lacks a live read for "+", ".join(missing)+". Re-read them with list_triggers (all pages) and get_trigger, pass every one, and run again.")
now=datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
t={}
for i in want:
  v=live[i]
  t[i]={'enabled':v.get('enabled'),'next_run_at':v.get('next_run_at'),'last_run':v.get('last_run'),'read_at':now}
  if 'cron_expression' in v: t[i]['cron_expression']=v['cron_expression']
# A schedule change shows here: the config's schedule text was written for
# source.cron, so a different live cron means that text is now wrong.
bad=[]
for r in cfg:
  s=r.get('source',{})
  if s.get('kind')=='trigger' and 'cron' in s and s['id'] in t and t[s['id']].get('cron_expression','')!=s['cron']:
    bad.append(f"{r['name']}: config cron {s['cron']!r}, live {t[s['id']].get('cron_expression','')!r}")
json.dump(t,open('triggers.json','w'),indent=1)
# build.py reads each row's `added` date so a routine that never ran reads
# "Not run yet", then Late (skills-evals#984). Fill it from the live record
# once, so a new row never needs a hand-typed date.
filled=[]
for r in cfg:
  s=r.get('source',{})
  if s.get('kind')=='trigger' and not r.get('added') and s['id'] in live:
    c=live[s['id']].get('created_at')
    if not c: sys.exit(f"STOP: {r['name']} has no `added` date and arg 1 lacks created_at for {s['id']}. Pass created_at (list_triggers gives it) and run again.")
    r['added']=c[:10]; filled.append(r['name'])
if filled:
  json.dump(cfg,open(H+'/config/routines.json','w'),indent=1); print("added dates filled:",filled)
if bad:
  sys.exit("STOP: schedule changed; rewrite schedule (ET) and source.cron in config/routines.json, then run again: "+"; ".join(bad))
th=json.load(open('threads.json'))
for suf,at in json.loads(sys.argv[2]).items():
  for x in th:
    if x['thread_id'].endswith(suf): x['last_activity_at']=at
json.dump(th,open('threads.json','w'),indent=1)
out={}
# Workflows read: every non-retired workflow row in config/routines.json, plus
# config/site.json extra_workflows ([[repo, file]]) for ones a row's note
# depends on without being a row (e.g. the job that fires a scheduled task).
wfs=[(r['source']['repo'],r['source']['workflow']) for r in cfg if r.get('source',{}).get('kind')=='workflow' and not r.get('retired')]
wfs+=[tuple(x) for x in site.get('extra_workflows',[]) if tuple(x) not in wfs]
for repo,wf in wfs:
  r=json.loads(subprocess.check_output(["gh","api",f"repos/{repo}/actions/workflows/{wf}/runs?per_page=4"]))
  out[f"{repo}:{wf}"]=[{k:x[k] for k in("created_at","status","conclusion","html_url")} for x in r["workflow_runs"]]
json.dump(out,open('workflow_runs.json','w'),indent=1)
wf={k:json.loads(subprocess.check_output(["gh","api",f"repos/{k.split(':')[0]}/actions/workflows/{k.split(':')[1]}"])) for k in out}
st={k:v["state"] for k,v in wf.items()}
filled=[]
for r in cfg:
  s=r.get('source',{})
  if s.get('kind')=='workflow' and not r.get('added'):
    k=next((k for k in wf if k.endswith(':'+s.get('workflow',''))),None)
    if k is None: sys.exit(f"STOP: {r['name']} has no `added` date and refresh.sh does not read workflow {s.get('workflow')}; add it to the workflow list in refresh.sh.")
    r['added']=wf[k]['created_at'][:10]; filled.append(r['name'])
if filled:
  json.dump(cfg,open(H+'/config/routines.json','w'),indent=1); print("added dates filled:",filled)
json.dump(st,open('workflow_states.json','w'),indent=1); print("workflow states",st)
heads={}
for repo in site.get('environment_review_repos',[]):
  r=json.loads(subprocess.check_output(["gh","api",f"repos/{repo}/pulls?state=open"]))
  print("open PRs",repo,[(p["number"],p["head"]["sha"][:7]) for p in r])
  heads[repo]=[p["head"]["sha"] for p in r]
json.dump(heads,open('open_pr_heads.json','w'))
EOF
bash "$SE/dashboard/refresh/half_built.sh"
# Paths are not tied to one session's container (2026-11-12: the refresh had
# to move sessions, and its baseline lived in the old session's scratchpad).
cd "$SE" && git fetch -q origin +persistent/eval-results:refs/remotes/origin/persistent/eval-results
S=${REFRESH_WORK:-/tmp/dashboard-refresh}; ER=$S/er_now; DS=$S/ds_now; rm -rf $ER $DS; mkdir -p $ER $DS
git archive origin/persistent/eval-results | tar -x -C $ER
python3 dashboard/build.py --results $ER --inputs "$DASHBOARD_HOME/inputs/" --config "$DASHBOARD_HOME/config/" --out $DS >/dev/null
for f in waiting threads routines cost_benefit_weeks refresh; do [ -s $DS/$f.json ] || { echo "STOP: build.py did not write $f.json this run"; exit 1; }; done
# explorer_private goes to the private artifact only, never to ds/ here.
if grep -q explorer_private dashboard/page/datasets.json 2>/dev/null; then
  P=${AGENTSKILLS_PRIVATE:-$(dirname "$SE")/adam-agentskills-private}
  ( cd "$P" && git fetch -q origin +persistent/eval-results:refs/remotes/origin/persistent/eval-results && git show origin/persistent/eval-results:explorer/private.json ) > $DS/explorer_private.json 2>/dev/null || { rm -f $DS/explorer_private.json; echo "STOP: cannot read explorer/private.json from adam-agentskills-private at $P; attach that repo (add_repo) and run again."; exit 1; }
fi
# Baseline = what was last published: $DASHBOARD_HOME/ds and watch/page_published.sha256,
# both written by dashboard/refresh/mark_published.sh after the uploads.
B=$DASHBOARD_HOME/ds
for f in $DS/*.json; do b=$(basename $f); [ "$b" = explorer_private.json ] && { [ "$(sha256sum $f | cut -d' ' -f1)" = "$(cat "$DASHBOARD_HOME/watch/private_published.sha256" 2>/dev/null)" ] || echo changed $b; continue; }; cmp -s $f $B/$b || echo changed $b; done
[ "$(sha256sum dashboard/page/index.html | cut -d' ' -f1)" = "$(cat "$DASHBOARD_HOME/watch/page_published.sha256" 2>/dev/null)" ] && echo page-same || echo PAGE-CHANGED
diff <(python3 -m json.tool $B/eval_allowance.json) <(python3 -m json.tool $DS/eval_allowance.json) | grep '^[<>]' | grep -v 'pace_room\|week_elapsed\|computed_at' || true
echo "built into $DS from skills-evals $(git rev-parse --short HEAD)"
