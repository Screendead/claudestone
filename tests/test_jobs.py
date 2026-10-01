"""scripts.jobs offline: remote_run is a local python that exits with scripted codes."""

import json
import subprocess
import sys
import time

import pytest

from scripts import jobs, remote_keep


def fake_remote_run(tmp_path, codes):
    """A remote_run whose n-th run exits codes[n] and appends its arguments to runs.txt."""
    runs = tmp_path / "runs.txt"
    code = (f"import pathlib, sys; p = pathlib.Path({str(runs)!r}); t = p.read_text() if p.exists() else ''; "
            f"p.write_text(t + ' '.join(sys.argv[1:]) + '\\n'); print('run', t.count('\\n'), flush=True); "
            f"raise SystemExit({codes!r}[t.count('\\n')])")
    return [sys.executable, "-c", code], runs


def wait_for(cond, timeout=20):
    deadline = time.time() + timeout
    while not cond():
        assert time.time() < deadline, "timed out"
        time.sleep(0.05)


@pytest.fixture
def work(tmp_path):
    d = tmp_path / "work"
    d.mkdir()
    return d


def prepare(tmp_path, work, monkeypatch, codes, resume=None):
    """A job written as `start` would, without launching its runner."""
    fake, runs = fake_remote_run(tmp_path, codes)
    with monkeypatch.context() as m:
        m.setattr(jobs, "REMOTE_RUN", fake)
        m.setattr(subprocess, "Popen", _no_runner(subprocess.Popen))
        jobs.start("j", work, ["python3", "search.py", "7"], 3, resume, jobs=tmp_path / "jobs")
    return tmp_path / "jobs" / "j", runs


def _no_runner(real):
    class Fake:
        pid = 0

    def popen(argv, **kw):
        return Fake() if argv[1:3] == ["-m", "scripts.jobs"] else real(argv, **kw)
    return popen


def test_a_lost_desktop_reruns_with_fresh_resume_args(tmp_path, work, monkeypatch):
    monkeypatch.setattr(remote_keep, "QUICK_LIMIT", 10)
    resume = "echo --done $JOB_RESTARTS; echo resumed >> marks.txt"
    d, runs = prepare(tmp_path, work, monkeypatch, [255, 255, 0], resume)
    assert jobs.run(d, answers=lambda: True, poll=0) == 0
    assert runs.read_text().splitlines() == [f"{work} --jobs 3 -- python3 search.py 7 --done {n}" for n in range(3)]
    assert (work / "marks.txt").read_text().split() == ["resumed"] * 3
    job = json.loads((d / "job.json").read_text())
    assert (job["restarts"], job["exit"]) == (2, 0)
    assert jobs.state(job) == "finished"


def test_a_failed_resume_ends_the_job(tmp_path, work, monkeypatch):
    d, runs = prepare(tmp_path, work, monkeypatch, [0], "exit 4")
    assert jobs.run(d, answers=lambda: True, poll=0) == 4
    assert not runs.exists()
    assert jobs.state(jobs.read(d)) == "failed"


def test_any_other_exit_ends_the_job(tmp_path, work, monkeypatch):
    d, runs = prepare(tmp_path, work, monkeypatch, [3, 0])
    assert jobs.run(d, answers=lambda: True, poll=0) == 3
    assert len(runs.read_text().splitlines()) == 1
    assert jobs.read(d)["restarts"] == 0


def test_gpus_reaches_remote_run(tmp_path, work, monkeypatch):
    fake, _ = fake_remote_run(tmp_path, [0])
    monkeypatch.setattr(jobs, "REMOTE_RUN", fake)
    monkeypatch.setattr(subprocess, "Popen", _no_runner(subprocess.Popen))
    job = jobs.start("g", work, ["python3", "x.py"], 2, jobs=tmp_path / "jobs", gpus=True)
    assert job["argv"][len(fake):] == [str(work), "--jobs", "2", "--gpus", "--", "python3", "x.py"]


def test_start_detaches_and_logs(tmp_path, work, monkeypatch):
    fake, runs = fake_remote_run(tmp_path, [0])
    monkeypatch.setattr(jobs, "REMOTE_RUN", fake)
    root = tmp_path / "jobs"
    job = jobs.start("j", work, ["python3", "x.py"], jobs=root)
    assert job["pid"] and job["exit"] is None
    wait_for(lambda: jobs.read(root / "j")["exit"] is not None)
    assert jobs.read(root / "j")["exit"] == 0
    log = (root / "j" / "log").read_text()
    assert "run 0" in log and "exit 0" in log
    assert "finished" in jobs.summary(root)[0]


def test_stop_ends_a_running_job(tmp_path, work, monkeypatch):
    monkeypatch.setattr(jobs, "REMOTE_RUN", [sys.executable, "-c", "import time; print('up', flush=True); time.sleep(60)"])
    root = tmp_path / "jobs"
    job = jobs.start("j", work, ["x"], jobs=root)
    wait_for(lambda: "up" in (root / "j" / "log").read_text())
    assert jobs.state(jobs.read(root / "j")) == "running"
    with pytest.raises(SystemExit):
        jobs.start("j", work, ["x"], jobs=root)
    assert jobs.stop("j", jobs=root, wait=10) == "j: stopped"
    wait_for(lambda: jobs.read(root / "j")["exit"] is not None)
    assert jobs.state(jobs.read(root / "j")) == "stopped"
    assert not jobs.alive(job["pid"])


def test_a_stale_pid_is_a_dead_job(tmp_path, work, monkeypatch):
    d, _ = prepare(tmp_path, work, monkeypatch, [0])
    p = subprocess.Popen([sys.executable, "-c", "pass"])
    p.wait()
    jobs.update(d, pid=p.pid)
    assert jobs.state(jobs.read(d)) == "dead"
    assert jobs.summary(tmp_path / "jobs")[0].startswith("j: dead")
    assert jobs.stop("j", jobs=tmp_path / "jobs") == "j: dead"


def test_a_live_pid_of_another_program_is_not_the_job(tmp_path, work, monkeypatch):
    d, _ = prepare(tmp_path, work, monkeypatch, [0])
    p = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(30)"])
    try:
        jobs.update(d, pid=p.pid)
        assert jobs.state(jobs.read(d)) == "dead"
    finally:
        p.kill()
        p.wait()
