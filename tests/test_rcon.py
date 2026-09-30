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
