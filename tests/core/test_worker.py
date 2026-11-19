"""Worker tests: JSON protocol driven against the fake GRBL."""

import threading
import time

from freecad.cnc_control.core.transport import MemoryTransport
from freecad.cnc_control.core.worker import (
    Worker,
    decode_json_line,
    encode_json_line,
)
from freecad.cnc_control.testing.fake_grbl import FakeGrbl


class Backend:
    """Injects a memory-pair factory and serves the fake GRBL on the peer."""

    def __init__(self) -> None:
        self.peer = None
        self.fake = FakeGrbl()
        self.stop = threading.Event()

    def factory(self, _params):
        controller, client = MemoryTransport.pair()
        self.peer = controller
        self.start_fake()  # the banner must flow before connect() reads it
        return client

    def start_fake(self) -> None:
        threading.Thread(
            target=self.fake.serve, args=(self.peer, self.stop), daemon=True
        ).start()

    def cleanup(self) -> None:
        self.stop.set()


class Session:
    """Worker running on its own thread, events collected in a list."""

    def __init__(self, factories) -> None:
        self.events = []
        self.worker = Worker(transport_factories=factories, emit=self.events.append)
        self.thread = threading.Thread(target=self.worker.run, daemon=True)
        self.thread.start()

    def submit(self, command: dict) -> None:
        self.worker.submit(command)

    def wait_event(self, name: str, timeout: float = 2.0):
        deadline = time.time() + timeout
        while time.time() < deadline:
            for event in self.events:
                if event.get("event") == name:
                    return event
            time.sleep(0.01)
        return None

    def shutdown(self) -> None:
        self.submit({"cmd": "shutdown"})
        self.thread.join(timeout=2.0)


def test_json_line_roundtrip():
    encoded = encode_json_line({"event": "connected", "version": "1.1h"})
    assert encoded.endswith(b"\n")
    assert decode_json_line(encoded.decode()) == {
        "event": "connected",
        "version": "1.1h",
    }


def test_connect_and_version():
    backend = Backend()
    session = Session({"memory": backend.factory})
    try:
        session.submit({"cmd": "connect", "params": {"kind": "memory"}})
        event = session.wait_event("connected")
        assert event is not None
        assert event["version"] == "1.1h"
    finally:
        backend.cleanup()
        session.shutdown()


def test_unknown_transport():
    session = Session({})
    try:
        session.submit({"cmd": "connect", "params": {"kind": "nope"}})
        event = session.wait_event("error")
        assert event is not None
        assert event["code"] == "unknown_transport"
    finally:
        session.shutdown()


def test_send_and_response_ok():
    backend = Backend()
    session = Session({"memory": backend.factory})
    try:
        session.submit({"cmd": "connect", "params": {"kind": "memory"}})
        session.wait_event("connected")
        session.submit({"cmd": "send", "params": {"line": "G0 X1"}})
        event = session.wait_event("response")
        assert event is not None
        assert event["kind"] == "ok"
    finally:
        backend.cleanup()
        session.shutdown()


def test_send_error_injected():
    backend = Backend()
    session = Session({"memory": backend.factory})
    try:
        session.submit({"cmd": "connect", "params": {"kind": "memory"}})
        session.wait_event("connected")
        backend.fake.inject_error(33)
        session.submit({"cmd": "send", "params": {"line": "G0 X999999"}})
        event = session.wait_event("response")
        assert event is not None
        assert event["kind"] == "error"
        assert event["code"] == 33
    finally:
        backend.cleanup()
        session.shutdown()


def test_status_event():
    backend = Backend()
    session = Session({"memory": backend.factory})
    try:
        session.submit({"cmd": "connect", "params": {"kind": "memory"}})
        session.wait_event("connected")
        session.submit({"cmd": "send", "params": {"line": "G0 X5 Y2"}})
        session.wait_event("response")
        session.submit({"cmd": "status"})
        event = session.wait_event("status")
        assert event is not None
        assert event["state"] == "Run"
        assert event["mpos"] == [5.0, 2.0, 0.0]
    finally:
        backend.cleanup()
        session.shutdown()


def test_stream_done():
    backend = Backend()
    session = Session({"memory": backend.factory})
    try:
        session.submit({"cmd": "connect", "params": {"kind": "memory"}})
        session.wait_event("connected")
        session.submit({"cmd": "stream", "params": {"lines": ["G0 X1", "G0 Y2"]}})
        event = session.wait_event("stream_done")
        assert event is not None
        assert event["sent"] == 2
        assert event["acked"] == 2
        assert event["completed"] is True
    finally:
        backend.cleanup()
        session.shutdown()


def test_send_without_connection():
    session = Session({})
    try:
        session.submit({"cmd": "send", "params": {"line": "G0 X1"}})
        event = session.wait_event("error")
        assert event is not None
        assert event["code"] == "not_connected"
    finally:
        session.shutdown()


def test_unknown_command():
    session = Session({})
    try:
        session.submit({"cmd": "does_not_exist"})
        event = session.wait_event("error")
        assert event is not None
        assert event["code"] == "unknown_command"
    finally:
        session.shutdown()


def test_disconnect_and_shutdown_events():
    backend = Backend()
    session = Session({"memory": backend.factory})
    try:
        session.submit({"cmd": "connect", "params": {"kind": "memory"}})
        session.wait_event("connected")
        session.submit({"cmd": "disconnect"})
        assert session.wait_event("disconnected") is not None
    finally:
        backend.cleanup()
        session.shutdown()
        assert session.wait_event("bye") is not None
        assert not session.thread.is_alive()
