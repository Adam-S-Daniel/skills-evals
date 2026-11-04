#!/usr/bin/env python3
"""Is adamdaniel.ai's Evals Explorer current, and if not, heal it or say so.

Driven by .github/workflows/site-freshness.yml (hourly, after "Site sync", and
on dispatch). Three checks decide:

  design  the source commit recorded in the site's provenance record
          (_data/tool_sources/skills-evals.yml on the site's main) is behind
          the newest skills-evals main commit that touched tool/index.html,
          and that commit is more than DESIGN_MAX_AGE old (its committer time).
  data    explorer/latest.json's `generated_at` is older than DATA_MAX_AGE.
  page    the live page, loaded in headless Chromium, did not draw the data
          (the `p.asof` line, built only after the data loaded; a
          `.panel.failure` means the page drew its error panel).

Mechanical fixes (`fix`): an open sync PR that is BEHIND its base gets
update-branch with the eval-improve App token; a stale design with neither a
sync PR nor a sync branch dispatches site-sync.yml. A missing token skips the
fix with a warning.

One issue, "Site freshness check is failing" (label half-built-or-broken, in
the fleet health audit's Kind/Severity/Finding-ID format), is created or
updated while any check fails and closed with a comment on the first fresh
run. When it has been open more than ESCALATE_AFTER and no fire marker comment
is newer than FIRE_COOLDOWN, the `fire` step starts the Sonnet routine; the
marker comment records the time and HTTP status only.

Nothing here prints a response body or personal data: gh and curl output is
parsed in memory, and logs carry check names, counts and status codes.

Pure decision functions take their inputs (times included); the gh, HTTP and
browser calls are thin functions at the bottom, injected in tests.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import urllib.request

EVALS_REPO = "Adam-S-Daniel/skills-evals"
DEFAULT_SITE_REPO = "Adam-S-Daniel/adamdaniel.ai"
SYNC_BRANCH = "tool-sync/skills-evals"
PROVENANCE_PATH = "_data/tool_sources/skills-evals.yml"
SOURCE_FILE = "tool/index.html"
DEFAULT_PAGE_URL = "https://adamdaniel.ai/tools/evals/"
DEFAULT_ASSET_URL = "https://adamdaniel.ai/assets/tools/skills-evals/index.html"
DATA_URL = ("https://raw.githubusercontent.com/Adam-S-Daniel/skills-evals/"
            "persistent/eval-results/explorer/latest.json")

DESIGN_MAX_AGE = timedelta(hours=2)
DATA_MAX_AGE = timedelta(hours=30)
ESCALATE_AFTER = timedelta(hours=1)
FIRE_COOLDOWN = timedelta(hours=6)
#: The fire API's text limit is 65,536 characters; stay well under it.
FIRE_TEXT_LIMIT = 60_000

ISSUE_TITLE = "Site freshness check is failing"
ISSUE_LABEL = "half-built-or-broken"
ISSUE_LABEL_COLOR = ("b60205", "A half-built or broken feature (fleet health audit)")
FINDING_ID = "skills-evals/site-freshness"
ISSUE_MARKER = "<!-- skills-evals:site-freshness -->"
FIRE_MARKER = "<!-- skills-evals:site-freshness-fire"  # + " at=<time> status=<code> -->"
CONFIG_MARKER = "<!-- skills-evals:site-freshness-config-missing -->"
FIRE_URL = "https://api.anthropic.com/v1/claude_code/routines/{id}/fire"
_ROUTINE_ID = re.compile(r"[A-Za-z0-9_-]{1,100}")
_REPO = re.compile(r"[A-Za-z0-9-]{1,39}/[A-Za-z0-9._-]{1,100}")

#: The reasons the page check can give; fixed text, never page content.
PAGE_OK = "drew"


@dataclass
class Check:
    name: str       # design | data | page
    ok: bool
    detail: str     # fixed text plus numbers and links; never a response body
    links: list = field(default_factory=list)


def parse_time(text: str) -> datetime:
    """An ISO-8601 time as an aware UTC datetime (GitHub's `Z` or an offset)."""
    value = datetime.fromisoformat(text.strip().replace("Z", "+00:00"))
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def stamp(when: datetime) -> str:
    return when.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def hours(delta: timedelta) -> str:
    return f"{delta.total_seconds() / 3600:.1f}"


# --------------------------------------------------------------------------
# Pure decisions
# --------------------------------------------------------------------------

def design_check(provenance_commit: str | None, newest_sha: str | None,
                 newest_time: datetime | None, relation: str | None,
                 now: datetime, links: list | None = None) -> Check:
    """Fresh when the site's source commit is the newest page commit or
    ahead of it (`relation` is the compare of newest...provenance: identical
    or ahead). Otherwise stale once the newest commit is older than
    DESIGN_MAX_AGE. An input that could not be read is a failure: a check
    that cannot see is not a pass."""
    links = links or []
    if not provenance_commit:
        return Check("design", False, "the site's provenance record could not be read", links)
    if not newest_sha or newest_time is None:
        return Check("design", False, f"the newest {SOURCE_FILE} commit could not be read", links)
    if provenance_commit == newest_sha or relation in ("identical", "ahead"):
        return Check("design", True, "the site has the newest page", links)
    age = now - newest_time
    short = newest_sha[:7]
    if age > DESIGN_MAX_AGE:
        return Check("design", False,
                     f"the site is behind {short}, committed {hours(age)} hours ago "
                     f"(limit {hours(DESIGN_MAX_AGE)})", links)
    return Check("design", True,
                 f"the site is behind {short}, committed {hours(age)} hours ago, "
                 "inside the limit", links)


def data_check(generated_at: str | None, now: datetime, links: list | None = None) -> Check:
    links = links or []
    if not generated_at:
        return Check("data", False, "latest.json has no readable generated_at", links)
    try:
        age = now - parse_time(generated_at)
    except ValueError:
        return Check("data", False, "latest.json has no readable generated_at", links)
    if age > DATA_MAX_AGE:
        return Check("data", False,
                     f"latest.json is {hours(age)} hours old (limit {hours(DATA_MAX_AGE)})", links)
    return Check("data", True, f"latest.json is {hours(age)} hours old", links)


def page_check(results: dict, links: list | None = None) -> Check:
    """`results` maps a URL to PAGE_OK or a fixed failure reason."""
    links = links or list(results)
    bad = {url: why for url, why in results.items() if why != PAGE_OK}
    if not results:
        return Check("page", False, "no page was loaded", links)
    if bad:
        return Check("page", False,
                     "; ".join(f"{url} did not draw ({why})" for url, why in sorted(bad.items())),
                     links)
    return Check("page", True, "the page drew its data", links)


def plan_fixes(design_ok: bool, sync_prs: list, branch_exists: bool | None) -> list:
    """Mechanical fixes. `sync_prs`: open sync PRs as {number, state} with the
    PR's mergeStateStatus. A BEHIND PR is updated, whatever the design check
    says (it will be stale soon). Dispatch only when the design is stale and
    neither a PR nor the branch exists; an unknown branch state dispatches
    nothing."""
    actions = [{"action": "update-branch", "number": pr["number"]}
               for pr in sync_prs if pr.get("state") == "BEHIND"]
    if not design_ok and not sync_prs and branch_exists is False:
        actions.append({"action": "dispatch-site-sync"})
    return actions


def plan_issue(failing: list, issue: dict | None, now: datetime,
               fire_configured: bool) -> dict:
    """What to do with the issue. `issue`: None or {number, created_at,
    comments: [{body, created_at}]}.

    {"action": none|create|update|close, "fire": bool, "config_comment": bool}
    Fire only for an issue open longer than ESCALATE_AFTER (a previous run's
    mechanical fixes did not help) with no fire marker newer than FIRE_COOLDOWN.
    Without the routine's variable and secret, say so once instead."""
    plan = {"action": "none", "fire": False, "config_comment": False}
    if not failing:
        plan["action"] = "close" if issue else "none"
        return plan
    if issue is None:
        plan["action"] = "create"
        return plan
    plan["action"] = "update"
    if now - parse_time(issue["created_at"]) <= ESCALATE_AFTER:
        return plan
    comments = issue.get("comments", [])
    recent = any(c["body"].lstrip().startswith(FIRE_MARKER)
                 and now - parse_time(c["created_at"]) < FIRE_COOLDOWN for c in comments)
    if recent:
        return plan
    if fire_configured:
        plan["fire"] = True
    elif not any(CONFIG_MARKER in c["body"] for c in comments):
        plan["config_comment"] = True
    return plan


def issue_body(failing: list, fixes: list, checked_at: datetime, run_url: str | None) -> str:
    lines = ["Kind: broken", "Severity: high", f"Finding-ID: {FINDING_ID}", ISSUE_MARKER, "",
             "adamdaniel.ai's Evals Explorer (https://adamdaniel.ai/tools/evals/) is not "
             "current. Failing checks:", ""]
    for check in failing:
        links = " ".join(f"<{url}>" for url in check.links)
        lines.append(f"- **{check.name}**: {check.detail}" + (f" ({links})" if links else ""))
    if fixes:
        lines += ["", "Mechanical fixes this run:"] + [f"- {fix}" for fix in fixes]
    lines += ["", f"Checked {stamp(checked_at)} (scripts/site_freshness.py).", "",
              "Recommendation: fix: read the Site sync runs "
              "(https://github.com/Adam-S-Daniel/skills-evals/actions/workflows/site-sync.yml) "
              "and the open sync PR on the site repo; after an hour open, the Sonnet routine "
              "(docs/routines/site-freshness-fixer.md) is fired once every 6 hours.", "",
              "This issue closes itself on the first fresh run."]
    if run_url:
        lines += ["", f"Workflow run: {run_url}"]
    lines += ["", "---", "_Filed by site-freshness.yml (scripts/site_freshness.py)._"]
    return "\n".join(lines) + "\n"


def fire_text(issue_url: str, failing: list) -> str:
    lines = [f"Site freshness issue: {issue_url}", "", "Failing checks:"]
    lines += [f"- {c.name}: {c.detail}" for c in failing]
    return "\n".join(lines)[:FIRE_TEXT_LIMIT]


def fire_marker(when: datetime, status: str) -> str:
    return f"{FIRE_MARKER} at={stamp(when)} status={status} -->"


# --------------------------------------------------------------------------
# Orchestration with injected gh
# --------------------------------------------------------------------------

def apply_issue_plan(gh, plan: dict, failing: list, fixes: list, issue: dict | None,
                     now: datetime, run_url: str | None) -> str | None:
    """Carry out plan_issue's issue action through `gh(args, token=None)`;
    returns the issue URL (or None). Never reads gh output beyond the URL."""
    body = issue_body(failing, fixes, now, run_url)
    url = None
    if plan["action"] == "create":
        ensure_label(gh)
        out = gh(["issue", "create", "-R", EVALS_REPO, "--title", ISSUE_TITLE,
                  "--label", ISSUE_LABEL, "--body", body])
        url = out.strip().splitlines()[-1] if out.strip() else None
    elif plan["action"] == "update":
        gh(["issue", "edit", str(issue["number"]), "-R", EVALS_REPO, "--body", body])
        url = f"https://github.com/{EVALS_REPO}/issues/{issue['number']}"
    elif plan["action"] == "close":
        gh(["issue", "close", str(issue["number"]), "-R", EVALS_REPO, "--reason", "completed",
            "--comment", "The site freshness checks passed on this run, so this issue closes.\n\n"
                         "<sub>🤖 Written by Claude Code on behalf of @Adam-S-Daniel</sub>"])
    if plan["config_comment"]:
        gh(["issue", "comment", str(issue["number"]), "-R", EVALS_REPO, "--body",
            f"{CONFIG_MARKER}\nThis issue has been open more than an hour, but the Sonnet "
            "routine was not fired: set the repository variable `SITE_FRESHNESS_ROUTINE_ID` "
            "and the secret `SITE_FRESHNESS_FIRE_BEARER` (see "
            "docs/routines/site-freshness-fixer.md). This is said once.\n\n"
            "<sub>🤖 Written by Claude Code on behalf of @Adam-S-Daniel</sub>"])
    return url


def ensure_label(gh) -> None:
    color, description = ISSUE_LABEL_COLOR
    try:
        gh(["label", "create", ISSUE_LABEL, "-R", EVALS_REPO, "--color", color,
            "--description", description])
    except GhError:
        pass  # it exists (a create never edits one), or the issue create will say


# --------------------------------------------------------------------------
# Thin I/O: gh, HTTP, browser
# --------------------------------------------------------------------------

class GhError(RuntimeError):
    """A gh call failed. Carries the command and exit code, never its output."""

    def __init__(self, args, code, missing=False):
        super().__init__(f"gh {' '.join(args[:2])} failed with exit code {code}")
        self.code = code
        self.missing = missing


def gh(args, token: str | None = None) -> str:
    env = dict(os.environ)
    if token:
        env["GH_TOKEN"] = token
    proc = subprocess.run(["gh", *args], capture_output=True, text=True, env=env, check=False)
    if proc.returncode != 0:
        missing = "404" in proc.stderr or "Not Found" in proc.stderr
        raise GhError(args, proc.returncode, missing)
    return proc.stdout


def http_get(url: str, timeout: int = 30, attempts: int = 3) -> str | None:
    for _ in range(attempts):
        try:
            if not url.startswith("https://"):
                return None
            with urllib.request.urlopen(url, timeout=timeout) as resp:  # noqa: S310
                return resp.read().decode("utf-8")
        except Exception:  # noqa: BLE001 - any failure is "unreadable"; nothing is printed
            continue
    return None


def provenance_commit(text: str | None) -> str | None:
    if not text:
        return None
    match = re.search(r"^commit:\s*([0-9a-f]{40})\s*$", text, re.M)
    return match.group(1) if match else None


def generated_at(text: str | None) -> str | None:
    if not text:
        return None
    try:
        value = json.loads(text).get("generated_at")
    except (ValueError, AttributeError):
        return None
    return value if isinstance(value, str) else None


def read_site_file(site_repo: str, path: str, token: str | None) -> str | None:
    try:
        return gh(["api", f"repos/{site_repo}/contents/{path}?ref=main",
                   "-H", "Accept: application/vnd.github.raw"], token)
    except GhError:
        return None


def newest_page_commit(token: str | None) -> tuple:
    try:
        rows = json.loads(gh(["api", f"repos/{EVALS_REPO}/commits?sha=main&path={SOURCE_FILE}"
                              "&per_page=1"], token))
        return rows[0]["sha"], parse_time(rows[0]["commit"]["committer"]["date"])
    except (GhError, ValueError, IndexError, KeyError, TypeError):
        return None, None


def compare_relation(base: str, head: str, token: str | None) -> str | None:
    try:
        return json.loads(gh(["api", f"repos/{EVALS_REPO}/compare/{base}...{head}",
                              "--jq", "{status: .status}"], token))["status"]
    except (GhError, ValueError, KeyError, TypeError):
        return None


def sync_state(site_repo: str, token: str | None) -> tuple:
    """(open sync PRs as {number, state, url, failing}, branch_exists or None)."""
    owner = site_repo.split("/")[0]
    prs = []
    try:
        rows = json.loads(gh(["api", f"repos/{site_repo}/pulls?state=open&per_page=10"
                              f"&head={owner}:{SYNC_BRANCH}"], token))
        for row in rows:
            info = json.loads(gh(["pr", "view", str(row["number"]), "-R", site_repo, "--json",
                                  "mergeStateStatus,url,statusCheckRollup"], token))
            failing = sorted({(c.get("name") or c.get("context") or "check")
                              for c in info.get("statusCheckRollup") or []
                              if (c.get("conclusion") or c.get("state")) in
                              ("FAILURE", "TIMED_OUT", "ERROR", "STARTUP_FAILURE")})
            prs.append({"number": row["number"], "state": info.get("mergeStateStatus"),
                        "url": info.get("url"), "failing": failing[:5]})
    except (GhError, ValueError, KeyError, TypeError):
        return [], None
    if prs:
        return prs, True
    try:
        gh(["api", f"repos/{site_repo}/branches/{SYNC_BRANCH.replace('/', '%2F')}"], token)
        return prs, True
    except GhError as err:
        return prs, False if err.missing else None


def browser_results(urls: list) -> dict:
    """Load each URL in headless Chromium: PAGE_OK when the data-dependent
    `p.asof` line appears, else a fixed reason. The page's text is never
    returned."""
    from playwright.sync_api import TimeoutError as PwTimeout, sync_playwright

    results = {}
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        try:
            for url in urls:
                page = browser.new_page()
                try:
                    response = page.goto(url, wait_until="domcontentloaded", timeout=45_000)
                    if response is None or response.status >= 400:
                        results[url] = f"http {response.status if response else 'none'}"
                        continue
                    try:
                        page.wait_for_selector("#app p.asof, #app .panel.failure",
                                               timeout=45_000)
                    except PwTimeout:
                        results[url] = "nothing drew in 45 seconds"
                        continue
                    results[url] = (PAGE_OK if page.query_selector("#app p.asof")
                                    else "the page drew its error panel")
                except Exception as err:  # noqa: BLE001
                    results[url] = f"browser error {type(err).__name__}"
                finally:
                    page.close()
        finally:
            browser.close()
    return results


def post_fire(routine_id: str, bearer: str, text: str) -> str:
    """POST the fire; returns the HTTP status code as text ('000' on a
    transport failure). The bearer goes to curl on stdin, never argv, and the
    response body is discarded."""
    body = json.dumps({"text": text})
    proc = subprocess.run(
        ["curl", "--silent", "--proto", "=https", "--max-time", "60", "--request", "POST",
         FIRE_URL.format(id=routine_id), "--header", "@-",
         "--header", "anthropic-version: 2023-06-01",
         "--header", "Content-Type: application/json", "--data-binary", body,
         "--output", os.devnull, "--write-out", "%{http_code}"],
        input=f"Authorization: Bearer {bearer}\n", capture_output=True, text=True, check=False)
    status = proc.stdout.strip()
    return status if proc.returncode == 0 and re.fullmatch(r"[0-9]{3}", status) else "000"


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------

def env_config() -> dict:
    site_repo = os.environ.get("SITE_REPO", DEFAULT_SITE_REPO)
    if not _REPO.fullmatch(site_repo):
        raise SystemExit("SITE_REPO is not owner/name")
    return {"site_repo": site_repo,
            "page_url": os.environ.get("SITE_PAGE_URL") or DEFAULT_PAGE_URL,
            "asset_url": os.environ.get("SITE_ASSET_URL") or DEFAULT_ASSET_URL}


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def write_output(name: str, value: str) -> None:
    path = os.environ.get("GITHUB_OUTPUT")
    if path:
        with open(path, "a", encoding="utf-8") as handle:
            handle.write(f"{name}={value}\n")


def check_to_json(check: Check) -> dict:
    return {"name": check.name, "ok": check.ok, "detail": check.detail, "links": check.links}


def check_from_json(row: dict) -> Check:
    return Check(row["name"], row["ok"], row["detail"], row.get("links", []))


def cmd_browser(args) -> int:
    cfg = env_config()
    results = browser_results([cfg["page_url"], cfg["asset_url"]])
    Path(args.out).write_text(json.dumps(results), encoding="utf-8")
    for url, why in sorted(results.items()):
        print(f"page {url}: {why}")
    return 0


def cmd_collect(args) -> int:
    cfg = env_config()
    now = utcnow()
    token = os.environ.get("APP_TOKEN") or os.environ.get("GH_TOKEN")
    site, repo_token = cfg["site_repo"], os.environ.get("GH_TOKEN")
    prov_url = f"https://github.com/{site}/blob/main/{PROVENANCE_PATH}"
    commit = provenance_commit(read_site_file(site, PROVENANCE_PATH, token))
    newest_sha, newest_time = newest_page_commit(repo_token)
    relation = (compare_relation(newest_sha, commit, repo_token)
                if commit and newest_sha and commit != newest_sha else None)
    design = design_check(commit, newest_sha, newest_time, relation, now, [prov_url])
    data = data_check(generated_at(http_get(DATA_URL)), now, [DATA_URL])
    browser = json.loads(Path(args.browser).read_text(encoding="utf-8")) \
        if Path(args.browser).exists() else {}
    page = page_check(browser, [cfg["page_url"], cfg["asset_url"]])
    prs, branch = sync_state(site, token)
    for pr in prs:
        if pr["url"]:
            design.links.append(pr["url"])
        if pr["failing"]:
            design.detail += f"; sync PR #{pr['number']} has failing checks: " + ", ".join(pr["failing"])
        if pr["state"] == "DIRTY":
            design.detail += f"; sync PR #{pr['number']} has a merge conflict"
    report = {"checked_at": stamp(now), "checks": [check_to_json(c) for c in (design, data, page)],
              "sync_prs": prs, "branch_exists": branch, "fixes": []}
    Path(args.out).write_text(json.dumps(report), encoding="utf-8")
    for check in (design, data, page):
        print(f"{check.name}: {'ok' if check.ok else 'FAILING'}: {check.detail}")
    return 0


def cmd_fix(args) -> int:
    cfg = env_config()
    report = json.loads(Path(args.report).read_text(encoding="utf-8"))
    design_ok = next(c["ok"] for c in report["checks"] if c["name"] == "design")
    app, job = os.environ.get("APP_TOKEN"), os.environ.get("GH_TOKEN")
    for action in plan_fixes(design_ok, report["sync_prs"], report["branch_exists"]):
        if action["action"] == "update-branch":
            label = f"update-branch on {cfg['site_repo']}#{action['number']}"
            if not app:
                print(f"::warning::{label} skipped: no GitHub App token")
                report["fixes"].append(f"{label}: skipped, no GitHub App token")
                continue
            try:
                gh(["api", "-X", "PUT",
                    f"repos/{cfg['site_repo']}/pulls/{action['number']}/update-branch"], app)
                report["fixes"].append(f"{label}: requested")
            except GhError as err:
                report["fixes"].append(f"{label}: failed (exit {err.code})")
        else:
            label = "dispatch site-sync.yml"
            try:
                gh(["workflow", "run", "site-sync.yml", "-R", EVALS_REPO, "--ref", "main"], job)
                report["fixes"].append(f"{label}: requested")
            except GhError as err:
                report["fixes"].append(f"{label}: failed (exit {err.code})")
    for line in report["fixes"]:
        print(line)
    Path(args.report).write_text(json.dumps(report), encoding="utf-8")
    return 0


def find_issue() -> dict | None:
    text = gh(["api", "--paginate", f"repos/{EVALS_REPO}/issues?state=open&labels={ISSUE_LABEL}"
               "&per_page=100", "--jq", '.[] | {number, created_at, body, pr: has("pull_request")} | tojson'])
    for line in text.splitlines():
        row = json.loads(line)
        if row["pr"] or ISSUE_MARKER not in (row["body"] or ""):
            continue
        comments = gh(["api", "--paginate", f"repos/{EVALS_REPO}/issues/{row['number']}/comments"
                       "?per_page=100", "--jq", ".[] | {body, created_at} | tojson"])
        return {"number": row["number"], "created_at": row["created_at"],
                "comments": [json.loads(c) for c in comments.splitlines() if c.strip()]}
    return None


def cmd_issue(args) -> int:
    now = utcnow()
    report = json.loads(Path(args.report).read_text(encoding="utf-8"))
    checks = [check_from_json(r) for r in report["checks"]]
    failing = [c for c in checks if not c.ok]
    configured = os.environ.get("FIRE_CONFIGURED") == "true"
    issue = find_issue()
    plan = plan_issue(failing, issue, now, configured)
    server = os.environ.get("GITHUB_SERVER_URL", "https://github.com")
    run_url = (f"{server}/{os.environ['GITHUB_REPOSITORY']}/actions/runs/{os.environ['GITHUB_RUN_ID']}"
               if os.environ.get("GITHUB_RUN_ID") and os.environ.get("GITHUB_REPOSITORY") else None)
    url = apply_issue_plan(gh, plan, failing, report["fixes"], issue, now, run_url)
    print(f"issue: {plan['action']}; fire: {plan['fire']}; failing: "
          f"{', '.join(c.name for c in failing) or 'none'}")
    if plan["fire"] and url:
        Path(args.fire_text).write_text(fire_text(url, failing), encoding="utf-8")
        write_output("fire", "true")
        write_output("issue_number", str(issue["number"]))
    if failing:
        print("::warning::" + "; ".join(f"{c.name}: {c.detail}" for c in failing))
    return 0


def cmd_fire(args) -> int:
    routine_id, bearer = os.environ.get("ROUTINE_ID", ""), os.environ.get("FIRE_BEARER", "")
    number = os.environ.get("ISSUE_NUMBER", "")
    if not _ROUTINE_ID.fullmatch(routine_id) or not bearer or not number.isdigit():
        print("::error::the routine id, the bearer or the issue number is missing or malformed")
        return 1
    status = post_fire(routine_id, bearer, Path(args.fire_text).read_text(encoding="utf-8"))
    print(f"fire API status: {status}")
    gh(["issue", "comment", number, "-R", EVALS_REPO, "--body",
        fire_marker(utcnow(), status) + "\nFired the site freshness routine; HTTP status "
        f"{status}.\n\n<sub>🤖 Written by Claude Code on behalf of @Adam-S-Daniel</sub>"])
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("browser"); p.add_argument("--out", required=True); p.set_defaults(fn=cmd_browser)
    p = sub.add_parser("collect"); p.add_argument("--browser", required=True)
    p.add_argument("--out", required=True); p.set_defaults(fn=cmd_collect)
    p = sub.add_parser("fix"); p.add_argument("--report", required=True); p.set_defaults(fn=cmd_fix)
    p = sub.add_parser("issue"); p.add_argument("--report", required=True)
    p.add_argument("--fire-text", required=True); p.set_defaults(fn=cmd_issue)
    p = sub.add_parser("fire"); p.add_argument("--fire-text", required=True); p.set_defaults(fn=cmd_fire)
    args = parser.parse_args(argv)
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
