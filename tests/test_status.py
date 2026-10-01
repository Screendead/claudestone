import os
"""scripts.status offline: nothing here asks a server or the desktop."""

import fcntl
import json

from redstone import docker_sats
from scripts import status


def test_a_marked_desktop_is_not_asked(tmp_path, monkeypatch):
    down = tmp_path / "dsat_unreachable"
    down.write_text("somewhere")
    monkeypatch.setattr(docker_sats, "HOST", "somewhere")
    monkeypatch.setattr(docker_sats, "DOWN_FILE", down)

    def asked(*a, **k):
        raise AssertionError("asked the desktop")
    monkeypatch.setattr(docker_sats, "docker", asked)
    names, why = status.desktop()
    assert names is None and why.startswith("marked unreachable")


def test_held_sees_another_holder_and_keeps_the_mtime(tmp_path):
    lock = tmp_path / "rig.lock"
    assert not status.held(lock) and not lock.exists()
    lock.touch()
    mtime = lock.stat().st_mtime_ns
    assert not status.held(lock)
    with open(lock, "a") as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        assert status.held(lock)
    assert lock.stat().st_mtime_ns == mtime


def test_plots_show_busy_owner_and_quiet(tmp_path, monkeypatch):
    records, st = tmp_path / "plots", tmp_path / "status"
    records.mkdir()
    st.mkdir()
    monkeypatch.setattr(status, "PLOT_RECORDS", records)
    monkeypatch.setattr(status, "STATUS", st)
    for name in ("xor", "and"):
        (records / f"{name}.lock").touch()
        (records / f"{name}.json").write_text(json.dumps({"server": "dsat1"}))
    os.utime(records / "and.json", (0, 0))
    (st / "xor.json").write_text(json.dumps({"text": "xor_a: step 3", "time": 1e12, "owner": "agent-7"}))
    with open(records / "xor.lock", "a") as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        lines = status.plot_lines()
    assert lines[0].startswith("BUSY xor on dsat1 [agent-7]: xor_a: step 3")
    assert lines[1].endswith(": and")


def test_a_satellite_run_of_a_plot_shows_busy_under_the_plot(tmp_path, monkeypatch):
    records, st = tmp_path / "plots", tmp_path / "status"
    records.mkdir()
    st.mkdir()
    monkeypatch.setattr(status, "PLOT_RECORDS", records)
    monkeypatch.setattr(status, "STATUS", st)
    for lock in ("xor.lock", "xor@sat1.lock", "xor@sat6.lock"):
        (records / lock).touch()
    (records / "xor.json").write_text(json.dumps({"server": "sat6"}))
    with open(records / "xor@sat6.lock", "a") as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        lines = status.plot_lines()
    assert len(lines) == 1 and lines[0].startswith("BUSY xor on sat6: last run")
    assert status.plot_lines()[0].startswith("idle xor on sat6")


def test_a_plot_without_a_status_file_is_dated_by_its_record(tmp_path, monkeypatch):
    records, st = tmp_path / "plots", tmp_path / "status"
    records.mkdir()
    st.mkdir()
    monkeypatch.setattr(status, "PLOT_RECORDS", records)
    monkeypatch.setattr(status, "STATUS", st)
    (records / "storage.lock").touch()
    (records / "storage.json").write_text(json.dumps({"server": "dsat1"}))
    assert status.plot_lines()[0].startswith("idle storage on dsat1: last run (")
    (records / "storage.json").write_text(json.dumps({"server": "dsat1", "owner": "wf-42"}))
    assert status.plot_lines()[0].startswith("idle storage on dsat1 [wf-42]: last run (")


def test_usage_reads_the_cache(tmp_path):
    cache = tmp_path / "usage.json"
    cache.write_text(json.dumps({"windows": [{"kind": "weekly_all", "percent": 24,
                                              "resets_at": "2026-10-05T15:00:00+00:00"}],
                                 "error": None, "last_success_at": 1.0}))
    assert status.usage_line(cache).startswith("usage: weekly 24% (resets ")
    assert status.usage_line(tmp_path / "missing.json").startswith("usage: nothing cached")
