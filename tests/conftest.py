import fcntl

import pytest

from redstone.harness import SERVER_DIR, Rig, ensure_server
from redstone.rcon import Rcon


@pytest.fixture(scope="session")
def rcon():
    ensure_server()
    # One test area and one data pack per server, so concurrent pytest runs take turns.
    with open(SERVER_DIR / "rig.lock", "w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        r = Rcon()
        yield r
        r.close()


@pytest.fixture
def rig(rcon):
    return Rig(rcon)
