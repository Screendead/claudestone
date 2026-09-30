import re
import socket
import struct
from pathlib import Path

PROPERTIES = Path(__file__).resolve().parent.parent / "server" / "server.properties"

AUTH, EXEC = 3, 2


class RconError(Exception):
    pass


class Rcon:
    def __init__(self, host="127.0.0.1", port=25575, password=None, timeout=10.0):
        if password is None:
            password = re.search(r"^rcon\.password=(.*)$", PROPERTIES.read_text(), re.M).group(1)
        self.sock = socket.create_connection((host, port), timeout=timeout)
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

    def cmd(self, command):
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
