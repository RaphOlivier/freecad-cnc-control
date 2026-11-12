"""Byte transports for controller links (virtual only in tests)."""

import os
import queue
import socket
import threading
from abc import ABC, abstractmethod
from typing import Self


class TransportError(Exception):
    """Transport-level failure (closed, broken connection)."""


class Transport(ABC):
    """Blocking byte transport with line helpers."""

    def __init__(self) -> None:
        self._closed = threading.Event()
        self._buffer = b""

    @abstractmethod
    def write(self, data: bytes) -> None:
        """Send raw bytes (G-code lines and real-time command bytes)."""

    @abstractmethod
    def read(self) -> bytes | None:
        """Block until bytes are available; None once closed and drained."""

    def close(self) -> None:
        self._closed.set()

    @property
    def is_closed(self) -> bool:
        return self._closed.is_set()

    def read_line(self) -> str | None:
        """Return the next line without its newline; None when closed."""
        while True:
            # Check the buffer FIRST: a previous read may already hold
            # complete lines (controllers can send several at once).
            if b"\n" in self._buffer:
                line, _, self._buffer = self._buffer.partition(b"\n")
                return line.decode(errors="replace").rstrip("\r")
            data = self.read()
            if data is None:
                if self._buffer:
                    line, self._buffer = self._buffer, b""
                    return line.decode(errors="replace")
                return None
            self._buffer += data

    def write_line(self, line: str) -> None:
        self.write(line.encode() + b"\n")

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()


class MemoryTransport(Transport):
    """In-memory transport; use pair() to create two linked endpoints."""

    def __init__(
        self,
        incoming: "queue.Queue[bytes]",
        outgoing: "queue.Queue[bytes]",
        closed: threading.Event,
    ) -> None:
        super().__init__()
        self._incoming = incoming
        self._outgoing = outgoing
        self._shared_closed = closed

    @classmethod
    def pair(cls) -> tuple["MemoryTransport", "MemoryTransport"]:
        closed = threading.Event()
        to_a: queue.Queue[bytes] = queue.Queue()
        to_b: queue.Queue[bytes] = queue.Queue()
        return cls(to_a, to_b, closed), cls(to_b, to_a, closed)

    def write(self, data: bytes) -> None:
        if self._shared_closed.is_set():
            raise TransportError("transport is closed")
        self._outgoing.put(data)

    def read(self) -> bytes | None:
        while True:
            try:
                return self._incoming.get(timeout=0.05)
            except queue.Empty:
                if self._shared_closed.is_set():
                    return None

    def close(self) -> None:
        self._shared_closed.set()

    @property
    def is_closed(self) -> bool:
        return self._shared_closed.is_set()


class SocketTransport(Transport):
    """Client transport over TCP; used against virtual test servers only."""

    def __init__(self, host: str, port: int) -> None:
        super().__init__()
        self._host = host
        self._port = port
        self._sock: socket.socket | None = None

    def open(self) -> None:
        self._sock = socket.create_connection((self._host, self._port), timeout=5.0)
        self._sock.settimeout(0.05)

    def write(self, data: bytes) -> None:
        if self._sock is None:
            raise TransportError("socket is not open")
        try:
            self._sock.sendall(data)
        except OSError as exc:
            raise TransportError(str(exc)) from exc

    def read(self) -> bytes | None:
        while not self._closed.is_set():
            if self._sock is None:
                return None
            try:
                data = self._sock.recv(4096)
            except TimeoutError:
                continue
            except OSError:
                return None
            if not data:
                return None  # EOF
            return data
        return None

    def close(self) -> None:
        super().close()
        if self._sock is not None:
            try:
                self._sock.close()
            except OSError:
                pass
            self._sock = None


class PtyTransport(Transport):
    """Master side of a pseudo-terminal; the fake GRBL serves on the slave fd.

    POSIX only (Linux/macOS); used by tests, never with real hardware.
    """

    def __init__(self) -> None:
        super().__init__()
        if os.name != "posix":
            raise TransportError("pty transport requires a POSIX system")
        self._master_fd: int | None = None
        self._slave_fd: int | None = None

    def open(self) -> None:
        import pty
        import termios

        self._master_fd, self._slave_fd = pty.openpty()
        os.set_blocking(self._master_fd, False)
        attrs = termios.tcgetattr(self._slave_fd)
        # No echo, and non-canonical mode: real-time bytes like '?' have no
        # newline and must be delivered to the reader immediately.
        attrs[3] &= ~(termios.ECHO | termios.ICANON)
        termios.tcsetattr(self._slave_fd, termios.TCSANOW, attrs)

    @property
    def slave_fd(self) -> int:
        if self._slave_fd is None:
            raise TransportError("pty is not open")
        return self._slave_fd

    def write(self, data: bytes) -> None:
        if self._master_fd is None:
            raise TransportError("pty is not open")
        os.write(self._master_fd, data)

    def read(self) -> bytes | None:
        import select

        while not self._closed.is_set():
            if self._master_fd is None:
                return None
            ready, _, _ = select.select([self._master_fd], [], [], 0.05)
            if ready:
                try:
                    return os.read(self._master_fd, 4096)
                except OSError:
                    return None
        return None

    def close(self) -> None:
        super().close()
        for fd in (self._master_fd, self._slave_fd):
            if fd is not None:
                try:
                    os.close(fd)
                except OSError:
                    pass
        self._master_fd = None
        self._slave_fd = None
