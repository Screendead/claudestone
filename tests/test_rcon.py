import fcntl

import pytest

from redstone.rcon import Rcon


def test_commands_to_one_port_take_turns(tmp_path):
    """Another client's command must not run while this one's is in flight: the server
    shares one output buffer between RCON clients."""
    path = tmp_path / "rcon.25575.lock"
    r = Rcon.__new__(Rcon)
    r._turn = open(path, "a")
    seen = []

    def probe(command):
        with open(path, "a") as other:
            with pytest.raises(BlockingIOError):
                fcntl.flock(other, fcntl.LOCK_EX | fcntl.LOCK_NB)
        seen.append(command)
        return "ok"

    r._cmd = probe
    assert r.cmd("list") == "ok" and seen == ["list"]
    with open(path, "a") as other:
        fcntl.flock(other, fcntl.LOCK_EX | fcntl.LOCK_NB)  # released after the command


def test_a_failed_command_releases_its_turn(tmp_path):
    path = tmp_path / "rcon.25575.lock"
    r = Rcon.__new__(Rcon)
    r._turn = open(path, "a")

    def boom(command):
        raise ConnectionError("dropped")

    r._cmd = boom
    with pytest.raises(ConnectionError):
        r.cmd("list")
    with open(path, "a") as other:
        fcntl.flock(other, fcntl.LOCK_EX | fcntl.LOCK_NB)


def _locked(path):
    with open(path, "a") as other:
        try:
            fcntl.flock(other, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return True
        return False


def test_a_sequence_holds_the_turn_across_commands_and_nests(tmp_path):
    path = tmp_path / "rcon.25575.lock"
    r = Rcon.__new__(Rcon)
    r._turn = open(path, "a")
    r._cmd = lambda command: command
    held = []
    with r.sequence():
        r.cmd("function probe")
        held.append(_locked(path))
        with r.sequence():
            r.cmd("data get storage x")
        held.append(_locked(path))  # the inner exit must not release the outer hold
    assert held == [True, True]
    assert not _locked(path)
    r.cmd("list")
    assert not _locked(path)


def test_a_failed_sequence_releases_its_turn(tmp_path):
    path = tmp_path / "rcon.25575.lock"
    r = Rcon.__new__(Rcon)
    r._turn = open(path, "a")
    with pytest.raises(ConnectionError):
        with r.sequence():
            raise ConnectionError("dropped")
    assert not _locked(path)


def test_rig_probe_sequences_hold_one_turn(tmp_path):
    """snapshot and command each read storage that their earlier commands set."""
    from redstone.harness import PACK, Rig

    path = tmp_path / "rcon.25575.lock"

    class Fake(Rcon):
        def __init__(self):
            self._turn = open(path, "a")
            self.log = []

        def _cmd(self, command):
            self.log.append((command, _locked(path)))
            return "ok 1" if "data get" in command else ""

    rig = Rig.__new__(Rig)
    rig.r = Fake()
    rig.origin, rig.size = (0, 56, 0), (8, 8, 8)
    rig.probe_count = 2
    rig.probed = [(0, 0, 0), (1, 0, 0)]
    rig.snapshot()
    assert rig.r.log[-1][0] == f"data get storage {PACK}:probe s"
    assert len(rig.r.log) == 4 and all(held for _, held in rig.r.log)
    rig.r.log.clear()
    rig.command("say hi")
    assert len(rig.r.log) == 2 and all(held for _, held in rig.r.log)
