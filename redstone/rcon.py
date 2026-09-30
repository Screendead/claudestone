import socket
import struct

AUTH, EXEC = 3, 2


class RconError(Exception):
    pass


class Rcon:
    def __init__(self, host="127.0.0.1", port=25575, password="redstone", timeout=10.0):
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
        # Vanilla reads one packet per socket read, so requests can't be pipelined.
        # Long responses arrive as consecutive 4096-byte packets; a shorter one ends it.
        self._send(EXEC, command)
        out = []
        while True:
            _, body = self._recv()
            out.append(body)
            if len(body.encode()) < 4096:
                return "".join(out)

    def close(self):
        self.sock.close()
