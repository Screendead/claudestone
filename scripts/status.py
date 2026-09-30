"""Everything running, on one screen, in a few seconds:

    python -m scripts.status

Jobs (scripts.jobs), the desktop search CPUs held (server/remote_run/), the servers (main,
laptop satellites, dsats: up and busy), each plot busy or idle with its server and status
line, the laptop's free memory and the plan usage last cached in ~/.claude/usage-cache.json.
Read-only: locks are probed, never waited for, and the desktop is asked one `docker ps`
(skipped while server/satellites/dsat_unreachable is set).
"""

import fcntl
import json
import re
import subprocess
import sys
import threading
import time
from datetime import datetime
from pathlib import Path

from redstone import docker_sats
from redstone.harness import _rcon_up
from redstone.servers import MAIN, PLOT_RECORDS, ROOT, SATELLITES
from redstone.watch import STATUS
from scripts import jobs
from scripts.remote_run import SLOTS, TOTAL_CPUS

USAGE = Path.home() / ".claude" / "usage-cache.json"
DESKTOP_WAIT = 6
RECENT = 3600  # an idle plot whose status is newer than this gets its own line


def held(path: Path) -> bool:
    """Whether another process holds path's flock. "a": opening must not touch the mtime
    the dsat reaper reads as use."""
    if not path.exists():
        return False
    with open(path, "a") as f:
        try:
            fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return True
        fcntl.flock(f, fcntl.LOCK_UN)
    return False


def ago(t: float) -> str:
    return jobs.duration(max(0, time.time() - t)) + " ago"


def read_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text())
    except (OSError, ValueError):
        return {}


def desktop() -> tuple[set[str] | None, str]:
    """(running dsat names, None if unknown; why unknown)."""
    if docker_sats.HOST is None:
        return None, "no desktop configured"
    if docker_sats.DOWN_FILE.exists():
        return None, f"marked unreachable {ago(docker_sats.DOWN_FILE.stat().st_mtime)}"
    try:
        # retry=False: call's recovery may close the ssh master, dropping every forward.
        p = docker_sats.docker("ps", "--filter", "name=^dsat", "--format", "{{.Names}}",
                               timeout=DESKTOP_WAIT - 1, retry=False, check=False)
    except docker_sats.DesktopError as e:
        return None, f"no answer ({e})"
    if p.returncode != 0:
        return None, f"docker ps failed: {(p.stderr or b'').decode(errors='replace').strip()[:100]}"
    return set(p.stdout.decode().split()), ""


def section(title: str, lines: list[str]) -> list[str]:
    return [title] + [f"  {x}" for x in lines or ["-"]]


def slot_lines() -> list[str]:
    """CPU slots held, and each remote_run process here, jobs or not."""
    taken = sum(held(SLOTS / f"cpu{i}.lock") for i in range(TOTAL_CPUS))
    out = [f"{taken} of {TOTAL_CPUS} desktop search CPUs held"]
    ps = subprocess.run(["ps", "-axo", "pid=,etime=,command="], capture_output=True, text=True).stdout
    for line in ps.splitlines():
        pid, etime, *argv = line.split()
        if argv[1:3] != ["-m", "scripts.remote_run"] or "--" not in argv:
            continue
        cut = argv.index("--")
        cpus = argv[argv.index("--jobs") + 1] if "--jobs" in argv[:cut] else "1"
        where = "/".join(Path(argv[3]).parts[-2:]) if len(argv) > 3 else "?"
        out.append(f"pid {pid} up {etime}, {cpus} cpu, {where}: {' '.join(argv[cut + 1:])[:80]}")
    return out


def server_lines(dsats: set[str] | None, why: str) -> list[str]:
    def one(s, up: bool | None) -> str:
        state = "unknown" if up is None else "busy" if up and held(s.lock) else "up" if up else "down"
        return f"{s.name}:{state}"

    out = [" ".join([one(MAIN, _rcon_up(MAIN.rcon_port)), *(one(s, _rcon_up(s.rcon_port)) for s in SATELLITES)])]
    if dsats is None:
        out.append(f"dsats: {why}")
    else:
        out.append(" ".join(one(s, s.name in dsats) for s in docker_sats.DOCKER_SATELLITES))
    return out


def plot_lines() -> list[str]:
    names = sorted({p.stem for p in PLOT_RECORDS.glob("*.lock")} | {p.stem for p in STATUS.glob("*.json")})
    busy, recent, quiet = [], [], []
    for name in names:
        server = read_json(PLOT_RECORDS / f"{name}.json").get("server", "?")
        status = read_json(STATUS / f"{name}.json")
        text = status.get("text", "")
        owner = f" [{status['owner']}]" if status.get("owner") else ""
        when = f" ({ago(status['time'])})" if status.get("time") else ""
        line = f"{name} on {server}{owner}: {text[:90]}{when}"
        if held(PLOT_RECORDS / f"{name}.lock"):
            busy.append("BUSY " + line)
        elif status.get("time", 0) > time.time() - RECENT:
            recent.append("idle " + line)
        else:
            quiet.append(name)
    return busy + recent + ([f"idle, nothing for {jobs.duration(RECENT)}: {' '.join(quiet)}"] if quiet else [])


def memory_line() -> str:
    try:
        out = subprocess.run(["memory_pressure", "-Q"], capture_output=True, text=True, timeout=5).stdout
    except (OSError, subprocess.TimeoutExpired) as e:
        return f"memory_pressure: {e}"
    m = re.search(r"free percentage: (\d+)%", out)
    total = re.search(r"has (\d+) \(", out)
    if not m:
        return "memory_pressure: no free percentage"
    gb = f" of {int(total.group(1)) / 2 ** 30:.0f} GB" if total else ""
    return f"laptop RAM {m.group(1)}% free{gb}"


def usage_line(path: Path = USAGE) -> str:
    cache = read_json(path)
    if not cache.get("windows"):
        return f"usage: nothing cached in {path}"
    names = {"session": "session", "weekly_all": "weekly"}
    parts = []
    for w in cache["windows"]:
        name = names.get(w.get("kind"), w.get("model") or w.get("kind"))
        try:
            resets = datetime.fromisoformat(w["resets_at"]).astimezone().strftime("%a %H:%M")
        except (KeyError, TypeError, ValueError):
            resets = "?"
        parts.append(f"{name} {w.get('percent', '?')}% (resets {resets})")
    when = f", cached {ago(cache['last_success_at'])}" if cache.get("last_success_at") else ""
    error = f", last error: {cache['error']}" if cache.get("error") else ""
    return "usage: " + ", ".join(parts) + when + error


def main() -> int:
    got: list = [None, "no answer within the wait"]

    def ask():
        got[:] = desktop()

    t = threading.Thread(target=ask, daemon=True)
    t.start()
    out = section("jobs", jobs.summary()) + section("desktop searches", slot_lines())
    plots = plot_lines()
    t.join(DESKTOP_WAIT)
    out += section("servers", server_lines(*got)) + section("plots", plots)
    out += [memory_line(), usage_line()]
    print("\n".join(out))
    return 0


if __name__ == "__main__":
    sys.exit(main())
