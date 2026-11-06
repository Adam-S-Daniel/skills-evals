"""Seal probes run INSIDE the eval-runner container. Prints JSON lines.

Never prints an environment VALUE: names only.
Usage: python3 -I seal_probe.py <wsl_host_ip> <listen_port> <example_ip>...
Set HOST_USER to the host account name so the probe can look for /home/<it>.
"""
import json
import os
import socket
import struct
import subprocess
import sys
import urllib.request

WSL_IP, LISTEN_PORT = sys.argv[1], int(sys.argv[2])
EXAMPLE_IPS = sys.argv[3:]
OUT = []


def rec(probe, sealed, evidence):
    OUT.append({"probe": probe, "sealed": sealed, "evidence": evidence})
    print(json.dumps(OUT[-1]), flush=True)


def tcp(host, port, timeout=2.0):
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return "CONNECTED"
    except socket.timeout:
        return "timeout"
    except OSError as exc:
        return type(exc).__name__ + ":" + (exc.strerror or str(exc))


def dns_udp(server, name="example.com", timeout=2.0):
    qid = 0x1234
    header = struct.pack(">HHHHHH", qid, 0x0100, 1, 0, 0, 0)
    q = b"".join(bytes([len(p)]) + p.encode() for p in name.split(".")) + b"\0"
    pkt = header + q + struct.pack(">HH", 1, 1)
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.settimeout(timeout)
    try:
        s.sendto(pkt, (server, 53))
        data, _ = s.recvfrom(512)
        rcode = data[3] & 0x0F
        ancount = struct.unpack(">H", data[6:8])[0]
        return f"ANSWERED rcode={rcode} answers={ancount}"
    except socket.timeout:
        return "timeout"
    except OSError as exc:
        return type(exc).__name__ + ":" + (exc.strerror or str(exc))
    finally:
        s.close()


def resolve(name):
    try:
        return "RESOLVED " + ",".join(sorted({a[4][0] for a in socket.getaddrinfo(name, 443, socket.AF_INET)}))
    except socket.gaierror as exc:
        return "gaierror:" + str(exc.args[-1])


def status():
    fields = {}
    for line in open("/proc/self/status"):
        k, _, v = line.partition(":")
        if k in ("Uid", "Gid", "CapInh", "CapPrm", "CapEff", "CapBnd", "CapAmb", "NoNewPrivs", "Seccomp", "Seccomp_filters"):
            fields[k] = v.strip()
    return fields


st = status()
rec("identity+caps", st.get("CapEff") == "0000000000000000" and st.get("CapBnd") == "0000000000000000" and st["Uid"].split()[0] == "1000" and st.get("Seccomp") == "2", st)

# Docker socket and other host sockets.
socks = []
for top in ("/run", "/var/run", "/tmp", "/home", "/mnt", "/work", "/src", "/"):
    for root, dirs, files in os.walk(top):
        if root.startswith(("/proc", "/sys", "/usr", "/lib")):
            dirs[:] = []
            continue
        if top == "/" and root != "/":
            dirs[:] = []
        for name in files + dirs:
            p = os.path.join(root, name)
            try:
                if os.path.exists(p) and (os.stat(p).st_mode & 0o170000) == 0o140000:
                    socks.append(p)
            except OSError:
                pass
named = [p for p in ("/var/run/docker.sock", "/run/docker.sock", "/run/host-services", "/run/guest-services", "/mnt/host", "/mnt/wsl", "/run/desktop") if os.path.exists(p)]
rec("no docker socket / host sockets", not socks and not named, {"unix_sockets": sorted(set(socks)), "named_paths_present": named})

mounts = []
for line in open("/proc/self/mountinfo"):
    parts = line.split()
    sep = parts.index("-")
    mounts.append({"root": parts[3], "point": parts[4], "opts": parts[5], "fstype": parts[sep + 1], "source": parts[sep + 2]})
binds = [m for m in mounts if m["root"] not in ("/",) and m["fstype"] not in ("proc", "tmpfs", "devpts", "mqueue", "sysfs", "cgroup2", "cgroup")]
rec("mounts", True, [f'{m["point"]} {m["fstype"]} {m["opts"].split(",")[0]} root={m["root"]}' for m in mounts if not m["point"].startswith(("/proc/", "/sys/", "/dev/"))])

home = os.environ.get("HOME", "")
cred_hits = []
for root, dirs, files in os.walk("/"):
    if root.startswith(("/proc", "/sys", "/usr/lib", "/usr/share", "/usr/local/lib")):
        dirs[:] = []
        continue
    for name in files + dirs:
        if name in (".credentials.json", ".claude.json", ".claude", ".gitconfig", ".ssh", ".aws", ".config", "hosts.yml", ".netrc"):
            cred_hits.append(os.path.join(root, name))
home_list = sorted(os.listdir(home)) if home and os.path.isdir(home) else None
rec("no host HOME or ~/.claude", not cred_hits and not os.path.exists("/home/" + os.environ.get("HOST_USER", "nobody")), {"HOME": home, "home_entries": home_list, "/home": sorted(os.listdir("/home")), "credential_like_paths": cred_hits})

names = sorted(os.environ)
proxy = [n for n in names if "proxy" in n.lower()]
rec("env names (values never printed)", not proxy, {"names": names, "proxy_names": proxy})

interop = {
    "/mnt/c": os.path.exists("/mnt/c"),
    "/init": os.path.exists("/init"),
    "cmd.exe_on_PATH": any(os.path.exists(os.path.join(d, "cmd.exe")) for d in os.environ.get("PATH", "").split(":")),
    "WSL_env": [n for n in names if n.startswith("WSL")],
    "binfmt_misc_mounted": os.path.isdir("/proc/sys/fs/binfmt_misc") and bool(os.listdir("/proc/sys/fs/binfmt_misc")),
}
pe = "/tmp/probe-pe.exe"
with open(pe, "wb") as f:
    f.write(b"MZ" + b"\0" * 126 + b"PE\0\0" + b"\0" * 128)
os.chmod(pe, 0o755)
try:
    r = subprocess.run([pe], capture_output=True, timeout=5)
    interop["exec_PE"] = f"ran rc={r.returncode}"
except OSError as exc:
    interop["exec_PE"] = type(exc).__name__ + ":" + exc.strerror
rec("no Windows interop", not interop["/mnt/c"] and not interop["/init"] and not interop["cmd.exe_on_PATH"] and not interop["WSL_env"] and interop["exec_PE"].startswith("OSError:Exec format"), interop)

# Egress.
https = {}
for url in ("https://example.com", "http://example.com", "https://api.anthropic.com"):
    try:
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        with opener.open(url, timeout=5) as resp:
            https[url] = f"HTTP {resp.status}"
    except Exception as exc:  # noqa: BLE001
        https[url] = type(exc).__name__ + ":" + str(getattr(exc, "reason", exc))[:80]
rec("https/http to the internet fails", not any(v.startswith("HTTP") for v in https.values()), https)
direct = {f"{ip}:{p}": tcp(ip, p) for ip in EXAMPLE_IPS + ["1.1.1.1", "8.8.8.8"] for p in (443, 80)}
rec("direct TCP to internet IPs fails", "CONNECTED" not in direct.values(), direct)

names_to_resolve = ["example.com", "api.anthropic.com", "host.docker.internal", "gateway.docker.internal", "http.docker.internal", "kubernetes.docker.internal", "docker-desktop", "host-gateway"]
res = {n: resolve(n) for n in names_to_resolve}
rec("external + Docker Desktop names do not resolve", not any(v.startswith("RESOLVED") for v in res.values()), {"resolv.conf": open("/etc/resolv.conf").read().split("\n"), "hosts": [l for l in open("/etc/hosts").read().split("\n") if l and not l.startswith("#")], "getaddrinfo": res})
udp = {s: dns_udp(s) for s in ("127.0.0.11", "8.8.8.8", "1.1.1.1", "192.168.65.7", "192.168.65.1", "192.168.65.254", "172.18.0.1", "172.17.0.1", WSL_IP, "10.255.255.254")}
rec("raw UDP DNS for example.com gets no answer", not any(v.startswith("ANSWERED rcode=0") and "answers=0" not in v for v in udp.values()), udp)

# Gateways and the host.
gw = None
for line in open("/proc/net/route").read().splitlines()[1:]:
    f = line.split()
    if f[1] == "00000000":
        gw = socket.inet_ntoa(struct.pack("<L", int(f[2], 16)))
my_ip = socket.gethostbyname(socket.gethostname()) if True else None
ports = (22, 53, 80, 443, 2375, 2376, 3128, 3129, 5000, 8080, 6443, LISTEN_PORT)
targets = ["192.168.65.1", "192.168.65.2", "192.168.65.3", "192.168.65.5", "192.168.65.6", "192.168.65.7", "192.168.65.254", "172.17.0.1", WSL_IP, "10.255.255.254"]
# the evalnet bridge's own gateway address (x.x.0.1 of our subnet)
sub_gw = ".".join(my_ip.split(".")[:2] + ["0", "1"])
targets.append(sub_gw)
host = {f"{t}:{p}": tcp(t, p, 1.0) for t in targets for p in ports}
connected = sorted(k for k, v in host.items() if v == "CONNECTED")
rec("host/gateway/192.168.65.x unreachable", not connected, {"default_route_gw": gw, "my_ip": my_ip, "subnet_gw": sub_gw, "connected": connected, "outcomes": sorted(set(host.values()))})

# bwrap under the profile.
r = subprocess.run(["bwrap", "--ro-bind", "/", "/", "--dev", "/dev", "--proc", "/proc", "--tmpfs", "/tmp", "--unshare-all", "--die-with-parent", "--", "sh", "-c", "id -u; ip link 2>/dev/null | grep -c '^[0-9]' || ls /sys/class/net | wc -l"], capture_output=True, text=True)
rec("bwrap works (unshare-all incl. net)", r.returncode == 0, {"rc": r.returncode, "stdout": r.stdout.split(), "stderr": r.stderr.strip()[:200]})

print(json.dumps({"summary": {o["probe"]: o["sealed"] for o in OUT}}))
