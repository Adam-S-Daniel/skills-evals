"""Scored eval facts shared by dashboard/build.py and scripts/explorer_data.py.

One copy of the logic that turns the results branch's `routine-results/` summaries into
paired and bare run rows (`scored_runs`), and of the summaries the dashboard page shows over
them (`skill_vs_no_skill`, `latest_summary`, `latest_per_test`, `bare_summary`; the page's
`eval_summary`, `eval_latest_summary`, `eval_latest` and `bare_summary` calcs, ported line
for line). The dashboard builds its `eval_runs` and `bare_runs` datasets from `scored_runs`;
the public explorer document carries the same rows and summaries for public subjects only.
Nothing is rounded here.
"""
import json
from datetime import datetime, timezone
from pathlib import Path


def iso(dt):
    return dt.astimezone(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def fired_at(run_name):
    stamp = run_name.split("-")[0]
    return iso(datetime.strptime(stamp, "%Y%m%dT%H%M%SZ").replace(tzinfo=timezone.utc))


def arm_model(d):
    model = (d.get("cross_model") or {}).get("model")
    if model:
        return model
    used = d.get("models_used") or []
    return ([m for m in used if "haiku" not in m] or used or [None])[0]


def objective(d):
    if not d.get("aggregate") and d.get("objective_checks") is not None:
        ch = d["objective_checks"]  # single-trial summary: no aggregate block
        return sum(1 for c in ch if c.get("passed")), len(ch)
    o = (d.get("aggregate") or {}).get("objective") or {}
    return o.get("mean_passed"), o.get("mean_total")


def judge(d):
    j = (d.get("aggregate") or {}).get("judge") or {}
    o = j.get("overall")
    return (o.get("mean") if isinstance(o, dict) else o), j.get("status")


def cost(d):
    if not d.get("aggregate"):
        return (d.get("agent") or {}).get("cost_usd")
    return ((d.get("aggregate") or {}).get("cost_usd") or {}).get("sum")


def add_costs(a, b):
    return None if a is None and b is None else (a or 0) + (b or 0)


def cli_version(d):
    return ((d.get("harness") or {}).get("version") or "").replace(" (Claude Code)", "")


def scored_runs(er, report_base):
    """(paired rows, bare rows), newest first: every scored paired run (with/without a skill or
    guidance section) and every bare baseline run under `routine-results/`, each bare run beside
    the newest paired run of its test and model. No placeholder rows: dashboard/build.py adds
    those, the explorer document never carries one."""
    rows, bare = [], []
    root = Path(er) / "routine-results"
    for run in sorted(root.iterdir()) if root.is_dir() else []:
        try:
            fired_at(run.name)
        except ValueError:
            continue  # not a `<stamp>-<id>` run folder
        for rep in run.rglob("report.md"):
            base = rep.parent
            arms = {}
            for s in base.rglob("summary.json"):
                if "trial-" in str(s):
                    continue
                try:
                    d = json.loads(s.read_text())
                except (OSError, ValueError, UnicodeDecodeError, RecursionError):
                    continue
                # An unreadable summary, or one with no arm, is not a scored arm.
                if isinstance(d, dict) and isinstance(d.get("arm"), str):
                    arms[d["arm"]] = (s, d)
            url = report_base + str(rep.relative_to(er))
            rel = base.relative_to(run).parts  # skill/ts[/fixture]
            if "with_guidance_full" in arms and "with_guidance_full_minus_section" in arms:
                # One trial per arm; the section's effect is full vs full minus the section.
                g, gm = arms["with_guidance_full"][1], arms["with_guidance_full_minus_section"][1]
                wp, tot = objective(g)
                wop, _ = objective(gm)
                if wp is None or wop is None:
                    continue
                sec = g.get("section") or base.parent.name
                rows.append({
                    "run_id": run.name, "fired_at": fired_at(run.name),
                    "fixture": "guidance/" + sec + "/" + (g.get("fixture_name") or ""),
                    "skill": "guidance/" + sec, "model": arm_model(g), "trials": 1,
                    "with_skill": wp, "without_skill": wop, "checks": tot, "gain": wp - wop,
                    "with_judge": None, "without_judge": None,
                    "judge": "skipped: checks decided" if (g.get("judge") or {}).get("status") == "skipped" else "not run",
                    "with_share": wp / tot if tot else None, "without_share": wop / tot if tot else None,
                    "cost_usd": add_costs(cost(g), cost(gm)),
                    "meter_points": None, "account_week_after": None,
                    "cli": cli_version(g), "report_url": url,
                })
                continue
            if "without_skill" in arms and "with_skill" not in arms:
                # Bare baseline (ADR 0012 addendum): one isolation arm, nothing of ours loaded.
                path, b = arms["without_skill"]
                bp, tot = objective(b)
                if bp is None:
                    continue
                sub = path.relative_to(base).parts
                bare.append({
                    "run_id": run.name, "fired_at": fired_at(run.name),
                    "fixture": rel[0] + ("/" + sub[0] if len(sub) > 2 else ""), "skill": rel[0],
                    "model": arm_model(b), "trials": b.get("n") or 1, "bare": bp, "checks": tot,
                    "bare_share": bp / tot if tot else None, "cost_usd": cost(b), "report_url": url,
                })
                continue
            if "with_skill" not in arms or "without_skill" not in arms:
                continue
            path, w = arms["with_skill"]
            wo = arms["without_skill"][1]
            wp, tot = objective(w)
            wop, _ = objective(wo)
            if wp is None or wop is None:
                continue
            wj, js = judge(w)
            woj, _ = judge(wo)
            sub = path.relative_to(base).parts
            md = ((w.get("usage") or {}).get("meter_delta") or {}).get("windows", {}).get("seven_day") or {}
            rows.append({
                "run_id": run.name, "fired_at": fired_at(run.name),
                "fixture": rel[0] + ("/" + sub[0] if len(sub) > 2 else ""), "skill": rel[0],
                "model": arm_model(w), "trials": w.get("n"),
                "with_skill": wp, "without_skill": wop, "checks": tot, "gain": wp - wop,
                "with_judge": wj, "without_judge": woj,
                "judge": "ran" if (wj is not None or woj is not None) else ("skipped: checks decided" if js == "skipped" else "not run"),
                "with_share": wp / tot if tot else None, "without_share": wop / tot if tot else None,
                "cost_usd": add_costs(cost(w), cost(wo)),
                "meter_points": None if md.get("delta") is None else md["delta"] * 100,
                "account_week_after": None if md.get("to") is None else md["to"] * 100,
                "cli": cli_version(w), "report_url": url,
            })
    rows.sort(key=lambda r: r["fired_at"], reverse=True)
    # Each bare run beside the newest paired run of the same test and model.
    latest = {}
    for r in rows:
        latest.setdefault((r["fixture"], r["model"]), r)
    for b in bare:
        p = latest.get((b["fixture"], b["model"]))
        if not p:  # older paired runs name only the skill (one fixture, no subfolder)
            q = latest.get((b["skill"], b["model"]))
            p = q if q and q["checks"] == b["checks"] else None
        b["paired_at"] = p["fired_at"] if p else None
        b["with_share"] = p["with_share"] if p else None
        b["without_share"] = p["without_share"] if p else None
    bare.sort(key=lambda r: r["fired_at"], reverse=True)
    return rows, bare


def is_skill_run(row):
    """A skill run, not a guidance one: guidance rows share the list as `guidance/<section>`."""
    return not str(row["skill"]).startswith("guidance/")


def _share(value):
    # The page adds a null share as 0 (JavaScript's null + number).
    return value or 0


def skill_vs_no_skill(rows):
    """Per model and overall (`All` first), over every scored skill run: runs where the skill
    scored higher, tied or lower, the average share of checks passed on each side, and the
    difference (`lift`). The page's `eval_summary`."""
    groups = {}
    for r in filter(is_skill_run, rows):
        for key in ("All", r["model"]):
            x = groups.setdefault(key, {"model": key, "runs": 0, "helped": 0, "tied": 0, "hurt": 0,
                                        "w": 0, "wo": 0})
            x["runs"] += 1
            if r["gain"] > 0:
                x["helped"] += 1
            elif r["gain"] < 0:
                x["hurt"] += 1
            else:
                x["tied"] += 1
            x["w"] += _share(r["with_share"])
            x["wo"] += _share(r["without_share"])
    return [{"model": x["model"], "runs": x["runs"], "helped": x["helped"], "tied": x["tied"],
             "hurt": x["hurt"], "with_avg": x["w"] / x["runs"], "without_avg": x["wo"] / x["runs"],
             "lift": (x["w"] - x["wo"]) / x["runs"]} for x in groups.values()]


def latest_summary(rows):
    """For the newest scored run of each skill test on each model: how many the skill won,
    tied and lost (one test re-run many times counts once). The page's `eval_latest_summary`."""
    latest = {}
    for r in filter(is_skill_run, rows):
        key = (r["fixture"], r["model"])
        if key not in latest or r["fired_at"] > latest[key]["fired_at"]:
            latest[key] = r
    v = list(latest.values())
    return {"tests": len(v), "helped": sum(1 for r in v if r["gain"] > 0),
            "tied": sum(1 for r in v if r["gain"] == 0), "hurt": sum(1 for r in v if r["gain"] < 0)}


LATEST_KEYS = ("fixture", "model", "with_share", "without_share", "with_skill", "without_skill",
               "checks", "fired_at", "run_id")


def latest_per_test(rows):
    """The newest scored run for each test (skill or guidance) on each model. The page's
    `eval_latest`."""
    seen = {}
    for r in sorted(rows, key=lambda r: r["fired_at"], reverse=True):
        seen.setdefault((r["fixture"], r["model"]), {k: r[k] for k in LATEST_KEYS})
    return list(seen.values())


def bare_summary(bare):
    """Per model and overall: the average share of checks passed by the bare model, by our setup
    without the skill and with it, over tests with both a bare and a paired run. The page's
    `bare_summary`."""
    groups = {}
    for r in bare:
        if r["bare_share"] is None or r["with_share"] is None or r["without_share"] is None:
            continue
        for key in ("All", r["model"]):
            x = groups.setdefault(key, {"model": key, "pairs": 0, "b": 0, "wo": 0, "w": 0,
                                        "bare_won": 0})
            x["pairs"] += 1
            x["b"] += r["bare_share"]
            x["wo"] += r["without_share"]
            x["w"] += r["with_share"]
            if r["bare_share"] > r["with_share"]:
                x["bare_won"] += 1
    return [{"model": x["model"], "pairs": x["pairs"], "bare": x["b"] / x["pairs"],
             "without": x["wo"] / x["pairs"], "with": x["w"] / x["pairs"],
             "setup_lift": (x["wo"] - x["b"]) / x["pairs"], "skill_lift": (x["w"] - x["wo"]) / x["pairs"],
             "bare_won": x["bare_won"]} for x in groups.values()]
