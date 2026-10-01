import contextlib
import fcntl
import re
import socket
import struct
from pathlib import Path

PROPERTIES = Path(__file__).resolve().parent.parent / "server" / "server.properties"

AUTH, EXEC = 3, 2


class RconError(Exception):
    pass


@contextlib.contextmanager
def port_turn(port: int):
    """Hold a port's turn without a connection, as Rcon.sequence does: a test running inside a
    Docker satellite's container talks to the server with the container's own lock, so the
    laptop side holds this one meanwhile and laptop clients of that port (scripts.look, say)
    wait instead of mixing their replies into the test's."""
    PROPERTIES.parent.mkdir(parents=True, exist_ok=True)
    with open(PROPERTIES.parent / f"rcon.{port}.lock", "a") as turn:
        fcntl.flock(turn, fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(turn, fcntl.LOCK_UN)


class Rcon:
    _held = 0  # depth of open sequence() blocks

    def __init__(self, host="127.0.0.1", port=25575, password=None, timeout=10.0):
        if password is None:
            password = re.search(r"^rcon\.password=(.*)$", PROPERTIES.read_text(), re.M).group(1)
        self.sock = socket.create_connection((host, port), timeout=timeout)
        # The server collects every RCON client's command output in one shared buffer
        # (DedicatedServer.runCommand), so replies of commands from two clients at once mix.
        # Commands to one port take turns across processes.
        self._turn = open(PROPERTIES.parent / f"rcon.{port}.lock", "a")
        self._id = 0
        if self._request(AUTH, password)[0] == -1:
            raise RconError("authentication failed")

    def _send(self, kind, body):
        self._id += 1
        payload = struct.pack("<ii", self._id, kind) + body.encode() + b"\x00\x00"
        self.sock.sendall(struct.pack("<i", len(payload)) + payload)
        return self._id

    def _recv_exact(self, n):
        buf = b""
        while len(buf) < n:
            chunk = self.sock.recv(n - len(buf))
            if not chunk:
                raise RconError("connection closed")
            buf += chunk
        return buf

    def _recv(self):
        (length,) = struct.unpack("<i", self._recv_exact(4))
        data = self._recv_exact(length)
        req_id, kind = struct.unpack("<ii", data[:8])
        return req_id, data[8:-2].decode()

    def _request(self, kind, body):
        self._send(kind, body)
        return self._recv()

    @contextlib.contextmanager
    def sequence(self):
        """Hold the port's turn across several commands, for a read that depends on state an
        earlier command set (a probe function, then the storage it wrote). Reentrant."""
        if not self._held:
            fcntl.flock(self._turn, fcntl.LOCK_EX)
        self._held += 1
        try:
            yield self
        finally:
            self._held -= 1
            if not self._held:
                fcntl.flock(self._turn, fcntl.LOCK_UN)

    def cmd(self, command):
        with self.sequence():
            return self._cmd(command)

    def _cmd(self, command):
        # Vanilla reads one packet per socket read, so requests can't be pipelined. A long
        # response arrives as several 4096-char packets with no end marker, so after a full
        # one we send a second request and read until its reply. Replies are matched by id:
        # one left over from an earlier command (e.g. after a timeout) is dropped.
        want = self._send(EXEC, command)
        out, sentinel = [], None
        while True:
            req_id, body = self._recv()
            if req_id == sentinel:
                return "".join(out)
            if req_id != want:
                continue
            out.append(body)
            if sentinel is None:
                if len(body) < 4000:
                    return body
                sentinel = self._send(EXEC, "")

    def close(self):
        self.sock.close()
        self._turn.close()
