"""End-to-end worker connect against the loopback fake GRBL socket.

This reproduces the panel's socket path: the real SocketTransport is created
by the worker's default factory, so the test fails if the worker forgets to
open the transport before waiting for the welcome banner. No serial port or
external host is involved.
"""

import socket
import threading
import time

from freecad.cnc_control.core.worker import Worker
from freecad.cnc_control.testing.fake_grbl import FakeGrbl


def _serve_once(listener: socket.socket) -> None:
    """Answer one loopback connection with the fake GRBL protocol."""
    conn, _ = listener.accept()
    with conn:
        fake = FakeGrbl()
        conn.sendall(fake.banner)
        while True:
            data = conn.recv(4096)
            if not data:
                return
            out = fake.process(data)
            if out:
                conn.sendall(out)


def _wait_event(events, name: str, timeout: float = 3.0):
    """Poll the event list until an event with the given name appears."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        for event in events:
            if event.get("event") == name:
                return event
        time.sleep(0.01)
    return None


def test_socket_connection_is_opened_before_the_welcome_banner():
    listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    listener.bind(("127.0.0.1", 0))
    listener.listen(1)
    port = listener.getsockname()[1]

    server = threading.Thread(target=_serve_once, args=(listener,), daemon=True)
    server.start()

    events = []
    worker = Worker(emit=events.append)
    runner = threading.Thread(target=worker.run, daemon=True)
    runner.start()
    worker.submit(
        {
            "cmd": "connect",
            "params": {"kind": "socket", "host": "127.0.0.1", "port": port},
        }
    )

    connected = _wait_event(events, "connected")
    assert connected is not None, events
    assert connected["version"] == FakeGrbl().version

    worker.stop()
    runner.join(timeout=2)
    listener.close()
    server.join(timeout=2)
