#!/usr/bin/env python3
"""Render the page against built datasets with a mocked dashboard runtime.

Usage: python3 dashboard/smoke/mk.py <page.html> <datasets dir> <work dir>
Writes <work dir>/test.html.
Live-only datasets (open_prs, merged_prs, open_issues, eval_ingests) are empty here; any other unknown id stays loading.
"""
import glob
import json
import os
import sys

page, ds_dir, work = sys.argv[1:4]
ds = {os.path.basename(f)[:-5]: json.load(open(f)) for f in glob.glob(os.path.join(ds_dir, "*.json"))}
for k in ["open_prs", "merged_prs", "open_issues", "eval_ingests"]:
    ds.setdefault(k, [])
mock = """<script>
const DS=%s; const calcs={}; let params={}; let cb=null;
window.dash={colors:['#36c','#c63'],loader(){},calc(id,o){calcs[id]=o;},
 data(id){ if(id in DS) return {status:'ok',data:DS[id]}; const c=calcs[id]; if(c){const ins=c.inputs.map(i=>this.data(i)); if(ins.every(x=>x.status==='ok')) return {status:'ok',data:c.fn(...ins.map(x=>x.data))}; return {status:'loading'};} return {status:'loading'};},
 onData(f){cb=f;}, params(){return params;}, setParams(p){Object.assign(params,p); cb&&cb();}, setLink(){}};
</script>""" % json.dumps(ds)
with open(os.path.join(work, "test.html"), "w") as f:
    f.write('<!doctype html><html><head><meta charset="utf-8"></head><body><div id="dash-root">' + mock + open(page).read()
            + "<script>setTimeout(()=>cb&&cb(),0)</script></div></body></html>")
