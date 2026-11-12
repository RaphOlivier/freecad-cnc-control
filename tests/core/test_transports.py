"""Socket and pty transports against the fake GRBL."""

import os
import socket
import threading

import pytest

from freecad.cnc_control.core.transport import PtyTransport, SocketTransport
from freecad.cnc_control.testing.fake_grbl import FakeGrbl


def test_socket_conversation():
    fake = FakeGrbl()
    server = socket.socket()
    server.bind(("127.0.0.1", 0))
    server.listen(1)
    port = server.getsockname()[1]
    stop = threading.Event()

    def run_server() -> None:
        server.settimeout(0.2)
        try:
            conn, _ = server.accept()
        except OSError:
            return
        conn.settimeout(0.2)
        conn.sendall(fake.banner)
        while not stop.is_set():
            try:
                data = conn.recv(4096)
            except TimeoutError:
                continue
            except OSError:
                break
            if not data:
                break
            out = fake.process(data)
            if out:
                conn.sendall(out)
        conn.close()

    thread = threading.Thread(target=run_server, daemon=True)
    thread.start()
    try:
        with SocketTransport("127.0.0.1", port) as client:
            client.open()
            assert client.read_line() == "Grbl 1.1h ['$' for help]"
            client.write_line("G0 X1")
            assert client.read_line() == "ok"
    finally:
        stop.set()
        server.close()


@pytest.mark.skipif(os.name != "posix", reason="pty transport is POSIX-only")
def test_pty_conversation():
    transport = PtyTransport()
    transport.open()
    fake = FakeGrbl()
    stop = threading.Event()
    thread = threading.Thread(target=fake.serve_fd, args=(transport.slave_fd, stop), daemon=True)
    thread.start()
    try:
        assert transport.read_line() == "Grbl 1.1h ['$' for help]"
        transport.write_line("G0 X2")
        assert transport.read_line() == "ok"
        transport.write(b"?")
        assert transport.read_line().startswith("<Run|MPos:2.000,0.000,0.000")
    finally:
        stop.set()
        transport.close()
