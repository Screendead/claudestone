import pytest

from redstone.harness import Rig, ensure_server
from redstone.rcon import Rcon


@pytest.fixture(scope="session")
def rcon():
    ensure_server()
    r = Rcon()
    yield r
    r.close()


@pytest.fixture
def rig(rcon):
    return Rig(rcon)
