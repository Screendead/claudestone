"""Long desktop jobs that outlive the shell that started them:

    python -m scripts.jobs start <name> <dir> [--jobs N] [--resume CMD] -- <cmd> [args]...
    python -m scripts.jobs status [<name>]
    python -m scripts.jobs stop <name>
    python -m scripts.jobs log <name> [-n LINES]

`start` detaches a runner (its own session, so it survives the launching process and any
task time limit) that runs `scripts.remote_run <dir> --jobs N -- <cmd>` under
`scripts.remote_keep`'s loop: a lost desktop (exit 255) waits for Docker and runs it again.
Everything the job prints goes to server/jobs/<name>/log; server/jobs/<name>/job.json
holds pid, cmd, dir, started, restarts and exit.

A dropped container copies nothing back, so the log is the only checkpoint. `--resume CMD`
runs here through the shell, in <dir>, before every start including the first, with
$JOB_NAME, $JOB_DIR, $JOB_LOG and $JOB_RESTARTS set: whatever it prints on stdout is split
into words and appended to <cmd> for that run, and it may also write files into <dir>
(which remote_run uploads). A resume that fails ends the job with its exit code.
"""

import argparse
import json
import os
import shlex
import signal
import subprocess
import sys
import time
from pathlib import Path

from redstone.servers import ROOT
from scripts import remote_keep

JOBS = ROOT / "jobs"
REPO = Path(__file__).resolve().parent.parent
REMOTE_RUN = [sys.executable, "-m", "scripts.remote_run"]
STOP_WAIT = 60  # remote_run removes its container on SIGTERM, one ssh call


class ResumeFailed(Exception):
    def __init__(self, code: int):
        super().__init__(code)
        self.code = code


def job_dir(name: str, jobs: Path = JOBS) -> Path:
    return jobs / name


def read(d: Path) -> dict | None:
    try:
        return json.loads((d / "job.json").read_text())
    except FileNotFoundError:
        return None


def write(d: Path, job: dict) -> None:
    tmp = d / f".job.{os.getpid()}.tmp"
    tmp.write_text(json.dumps(job, indent=1))
    tmp.replace(d / "job.json")


def update(d: Path, **fields) -> dict:
    job = read(d) | fields
    write(d, job)
    return job


def alive(pid: int | None) -> bool:
    """Whether pid is a running jobs runner (a reused pid belongs to something else)."""
    if not pid:
        return False
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        pass
    out = subprocess.run(["ps", "-o", "stat=,command=", "-p", str(pid)], capture_output=True, text=True).stdout
    return "scripts.jobs" in out and not out.lstrip().startswith("Z")


def state(job: dict) -> str:
    """running, stopped, finished (exit 0), failed (exit N) or dead (gone without an exit)."""
    if job.get("exit") is None:
        return "running" if alive(job.get("pid")) else "dead"
    if job.get("stopped"):
        return "stopped"
    return "finished" if job["exit"] == 0 else "failed"


def say(log, msg: str) -> None:
    print(f"jobs {time.strftime('%H:%M:%S')}: {msg}", file=log, flush=True)


def resume(d: Path, job: dict) -> list[str]:
    job = update(d, restarts=job["restarts"] + 1) if job.get("launched") else update(d, launched=True)
    say(sys.stderr, f"start {job['restarts'] + 1}" if job["restarts"] else "start")
    if not job.get("resume"):
        return []
    env = os.environ | {"JOB_NAME": job["name"], "JOB_DIR": job["dir"], "JOB_LOG": str(d / "log"),
                        "JOB_RESTARTS": str(job["restarts"])}
    p = subprocess.run(job["resume"], shell=True, cwd=job["dir"], env=env, stdout=subprocess.PIPE, text=True)
    if p.returncode != 0:
        say(sys.stderr, f"resume exited {p.returncode}")
        raise ResumeFailed(p.returncode)
    args = shlex.split(p.stdout)
    if args:
        text = " ".join(args)
        say(sys.stderr, f"resume args: {text if len(text) < 200 else text[:200] + '...'}")
    return args


def run(d: Path, answers=remote_keep.docker_answers, poll: float = remote_keep.POLL) -> int:
    """The runner: remote_keep's loop over the job's argv, its exit written to job.json."""
    job = read(d)
    code = None
    try:
        code = remote_keep.keep(job["argv"], answers=answers, poll=poll, before=lambda: resume(d, read(d)))
    except ResumeFailed as e:
        code = e.code
    except SystemExit as e:
        code = e.code if isinstance(e.code, int) else 1
        raise
    finally:
        update(d, exit=code if code is not None else 1, ended=time.time())
        say(sys.stderr, f"exit {code}")
    return code


def start(name: str, directory: Path, cmd: list[str], cpus: int = 1, resume_cmd: str | None = None,
          jobs: Path = JOBS) -> dict:
    d = job_dir(name, jobs)
    old = read(d)
    if old and state(old) == "running":
        raise SystemExit(f"jobs: {name} is running (pid {old['pid']}); stop it first")
    if not directory.is_dir():
        raise SystemExit(f"jobs: {directory} is not a directory")
    d.mkdir(parents=True, exist_ok=True)
    directory = directory.resolve()
    job = {"name": name, "cmd": cmd, "dir": str(directory), "jobs": cpus, "resume": resume_cmd,
           "argv": [*REMOTE_RUN, str(directory), "--jobs", str(cpus), "--", *cmd],
           "started": time.time(), "restarts": 0, "exit": None, "pid": None}
    write(d, job)
    with open(d / "log", "a") as log:
        say(log, f"--- {name}: {shlex.join(cmd)} in {directory}")
        p = subprocess.Popen([sys.executable, "-m", "scripts.jobs", "run", str(d)], cwd=REPO,
                             stdin=subprocess.DEVNULL, stdout=log, stderr=log, start_new_session=True)
    return update(d, pid=p.pid)


def stop(name: str, jobs: Path = JOBS, wait: float = STOP_WAIT) -> str:
    d = job_dir(name, jobs)
    job = read(d)
    if job is None:
        raise SystemExit(f"jobs: no job {name}")
    if state(job) != "running":
        return f"{name}: {state(job)}"
    update(d, stopped=True)
    os.kill(job["pid"], signal.SIGTERM)
    deadline = time.time() + wait
    while alive(job["pid"]) and time.time() < deadline:
        time.sleep(0.2)
    return f"{name}: {'stopped' if not alive(job['pid']) else f'still running (pid {job['pid']})'}"


def tail(path: Path, n: int) -> list[str]:
    try:
        with open(path, "rb") as f:
            f.seek(0, os.SEEK_END)
            size = f.tell()
            f.seek(max(0, size - max(64 * 1024, 400 * n)))
            return f.read().decode(errors="replace").splitlines()[-n:]
    except FileNotFoundError:
        return []


def duration(seconds: float) -> str:
    s = int(seconds)
    return f"{s // 86400}d{s % 86400 // 3600}h" if s >= 86400 else f"{s // 3600}h{s % 3600 // 60:02d}m" if s >= 3600 \
        else f"{s // 60}m{s % 60:02d}s"


def summary(jobs: Path = JOBS, names: list[str] | None = None) -> list[str]:
    """One line per job: name, state, uptime, restarts, last log line."""
    dirs = [job_dir(n, jobs) for n in names] if names else sorted(p for p in jobs.glob("*") if (p / "job.json").exists())
    lines = []
    for d in dirs:
        job = read(d)
        if job is None:
            lines.append(f"{d.name}: no such job")
            continue
        st = state(job)
        if st in ("running", "dead"):
            st += f" {duration(time.time() - job['started'])}"
            if st.startswith("running"):
                st += f" pid {job['pid']}"
        else:
            st += f" (exit {job['exit']}) {duration(time.time() - job.get('ended', job['started']))} ago"
        last = tail(d / "log", 1)
        lines.append(f"{job['name']}: {st}, {job['restarts']} restarts, {job['jobs']} cpu"
                     f"{'s' if job['jobs'] != 1 else ''}  | {last[0][:100] if last else ''}")
    return lines


def main(argv: list[str]) -> int:
    if argv[:1] == ["run"]:
        return run(Path(argv[1]))
    cmd = []
    if "--" in argv:
        cut = argv.index("--")
        argv, cmd = argv[:cut], argv[cut + 1:]
    ap = argparse.ArgumentParser(prog="python -m scripts.jobs", description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="action", required=True)
    s = sub.add_parser("start")
    s.add_argument("name")
    s.add_argument("dir", type=Path)
    s.add_argument("--jobs", type=int, default=1)
    s.add_argument("--resume")
    sub.add_parser("status").add_argument("name", nargs="?")
    sub.add_parser("stop").add_argument("name")
    lg = sub.add_parser("log")
    lg.add_argument("name")
    lg.add_argument("-n", type=int, default=20)
    a = ap.parse_args(argv)
    if a.action == "start":
        if not cmd:
            ap.error("start needs -- <cmd>")
        job = start(a.name, a.dir, cmd, a.jobs, a.resume)
        print(f"{a.name}: started, pid {job['pid']}, log {job_dir(a.name) / 'log'}")
    elif a.action == "status":
        print("\n".join(summary(names=[a.name] if a.name else None)) or "no jobs")
    elif a.action == "stop":
        print(stop(a.name))
    else:
        if read(job_dir(a.name)) is None:
            raise SystemExit(f"jobs: no job {a.name}")
        print("\n".join(tail(job_dir(a.name) / "log", a.n)))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
