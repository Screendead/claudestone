"""scripts.remote_keep offline: the job is a local python that exits with scripted codes."""

import signal
import subprocess
import sys
from pathlib import Path

from scripts import remote_keep as rk


def job(tmp_path, codes):
    """A command whose n-th run exits codes[n] and appends n to runs.txt."""
    runs = tmp_path / "runs.txt"
    code = (f"import pathlib; p = pathlib.Path({str(runs)!r}); n = len(p.read_text().split()) if p.exists() else 0; "
            f"p.write_text((p.read_text() if p.exists() else '') + f'{{n}} '); raise SystemExit({codes!r}[n])")
    return [sys.executable, "-c", code], runs


def test_a_lost_desktop_waits_for_docker_then_reruns(tmp_path, monkeypatch):
    monkeypatch.setattr(rk, "QUICK_LIMIT", 10)
    cmd, runs = job(tmp_path, [255, 255, 0])
    polls = iter([False, True, True])
    assert rk.keep(cmd, answers=lambda: next(polls), poll=0) == 0
    assert runs.read_text().split() == ["0", "1", "2"]


def test_any_other_exit_ends_the_watch(tmp_path):
    cmd, runs = job(tmp_path, [3, 0])
    assert rk.keep(cmd, answers=lambda: True, poll=0) == 3
    assert runs.read_text().split() == ["0"]


def test_quick_repeated_losses_give_up(tmp_path):
    cmd, runs = job(tmp_path, [255] * 5)
    assert rk.keep(cmd, answers=lambda: True, poll=0) == 255
    assert len(runs.read_text().split()) == rk.QUICK_LIMIT


def test_sigterm_stops_the_job_and_the_watch():
    sleeper = [sys.executable, "-c", "import time; print('up', flush=True); time.sleep(60)"]
    p = subprocess.Popen([sys.executable, "-c", f"import sys; from scripts import remote_keep as rk; sys.exit(rk.keep({sleeper!r}))"],
                         cwd=Path(__file__).resolve().parent.parent, stdout=subprocess.PIPE, text=True)
    try:
        assert p.stdout.readline().strip() == "up"
        p.terminate()
        assert p.wait(timeout=10) == 128 + signal.SIGTERM
    finally:
        p.kill()
