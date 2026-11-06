"""Derive the bwrap seccomp profile from Docker's default (stdin -> stdout)."""
import copy, json, sys
BWRAP = ["clone", "clone3", "mount", "pivot_root", "sethostname", "setns",
         "umount2", "unshare"]
src = json.load(sys.stdin)
out = copy.deepcopy(src)
rules = []
for rule in out["syscalls"]:
    names = rule["names"]
    # Docker's clone/clone3 rules that apply only WITHOUT CAP_SYS_ADMIN (the
    # flag-masked clone allow and clone3's ENOSYS) are superseded below.
    if set(names) <= {"clone", "clone3"} and "CAP_SYS_ADMIN" in rule.get("excludes", {}).get("caps", []):
        continue
    if rule.get("includes", {}).get("caps") == ["CAP_SYS_ADMIN"]:
        rule["names"] = [n for n in names if n not in BWRAP]
    rules.append(rule)
idx = next(i for i, r in enumerate(rules) if r.get("includes", {}).get("caps") == ["CAP_SYS_ADMIN"])
rules.insert(idx + 1, {
    "names": BWRAP,
    "action": "SCMP_ACT_ALLOW",
    "comment": "skills-evals: bubblewrap's user, mount, PID and UTS namespaces as uid 1000 with no capabilities (docker/eval-runner/Dockerfile)",
})
out["syscalls"] = rules
sys.stdout.write(json.dumps(out, indent="\t") + "\n")
