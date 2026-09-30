"""Keep a resumable desktop job going across desktop drops.

    python -m scripts.remote_keep -- <cmd> [args]...

<cmd> runs here, and is usually a script that rebuilds its resume state from the log it
streamed and then calls `scripts.remote_run` (a dropped container copies nothing back, so
the laptop's log is the only checkpoint). Exit 255, remote_run's code for a lost desktop,
waits until the desktop's Docker answers and runs <cmd> again; any other exit ends the
watch with that code. SIGTERM or Ctrl-C stops <cmd>, whose remote_run then stops its
container.
"""

import signal
import subprocess
import sys
import time

from redstone import docker_sats

LOST = 255
POLL = 30
# A job that is lost this quickly this many times in a row is failing, not being dropped.
QUICK, QUICK_LIMIT = 60, 3


def say(msg: str) -> None:
    print(f"remote_keep {time.strftime('%H:%M:%S')}: {msg}", file=sys.stderr, flush=True)


def docker_answers() -> bool:
    try:
        return subprocess.run(["ssh", "-o", "ConnectTimeout=5", docker_sats.HOST, "docker", "version"],
                              capture_output=True, timeout=20).returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        return False


def keep(cmd: list[str], answers=docker_answers, poll: float = POLL) -> int:
    child = None

    def stop(signum, frame):
        if child and child.poll() is None:
            child.terminate()
            child.wait()
        sys.exit(128 + signum)

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    quick = 0
    while True:
        t0 = time.monotonic()
        child = subprocess.Popen(cmd)
        code = child.wait()
        if code != LOST:
            return code
        quick = quick + 1 if time.monotonic() - t0 < QUICK else 0
        if quick >= QUICK_LIMIT:
            say(f"lost {quick} times within {QUICK} s each; giving up")
            return code
        say("desktop lost; waiting for its Docker")
        while not answers():
            time.sleep(poll)
        say("desktop back; resuming")


def main(argv: list[str]) -> int:
    if "--" not in argv or argv.index("--") == len(argv) - 1:
        raise SystemExit("usage: python -m scripts.remote_keep -- <cmd> [args]...")
    return keep(argv[argv.index("--") + 1:])


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
