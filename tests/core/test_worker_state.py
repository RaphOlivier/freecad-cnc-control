"""E8.2: explicit connection state managed by the Worker.

State must always be announced through "connection_state" events (including
the initial disconnected state at run start) and transitions must be coached:
no implicit reconnect, no commands racing a stream except status/cancel.
"""

import time

from tests.core.test_worker import Backend, Session


def wait_state(session, value: str, timeout: float = 2.0) -> bool:
    """Wait for a connection_state event with the given value (any position)."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        for event in session.events:
            if (
                event.get("event") == "connection_state"
                and event.get("value") == value
            ):
                return True
        time.sleep(0.01)
    for event in session.events:
        if event.get("event") == "connection_state" and event.get("value") == value:
            return True
    return False


def _connect(session):
    session.submit({"cmd": "connect", "params": {"kind": "memory"}})
    assert session.wait_event("connected") is not None


def test_initial_state_event_is_disconnected():
    session = Session({})
    try:
        assert wait_state(session, "disconnected")
        assert session.worker.state == "disconnected"
    finally:
        session.shutdown()


def test_connect_then_disconnect_transitions():
    backend = Backend()
    session = Session({"memory": backend.factory})
    try:
        assert wait_state(session, "disconnected")
        _connect(session)
        assert wait_state(session, "connected")
        assert session.worker.state == "connected"
        session.submit({"cmd": "disconnect"})
        assert session.wait_event("disconnected") is not None
        assert wait_state(session, "disconnected")
        assert session.worker.state == "disconnected"
    finally:
        backend.cleanup()
        session.shutdown()


def test_connect_while_connected_refused():
    backend = Backend()
    session = Session({"memory": backend.factory})
    try:
        _connect(session)
        session.submit({"cmd": "connect", "params": {"kind": "memory"}})
        event = session.wait_event("error")
        assert event is not None
        assert event["code"] == "already_connected"
        assert session.worker.state == "connected"
    finally:
        backend.cleanup()
        session.shutdown()


def test_streaming_state_lifecycle():
    backend = Backend()
    session = Session({"memory": backend.factory})
    try:
        _connect(session)
        # Silent link: the stream blocks, so we can observe the mid-flight state.
        backend.stop_fake()
        session.submit({"cmd": "stream", "params": {"confirmed": True, "lines": ["G0 X1", "G0 Y2"]}})
        assert wait_state(session, "streaming", timeout=5.0)
        assert session.worker.state == "streaming"
        session.worker.cancel()
        done = session.wait_event("stream_done")
        assert done is not None and done["cancelled"] is True
        assert wait_state(session, "connected")
        assert session.worker.state == "connected"
    finally:
        backend.cleanup()
        session.shutdown()


def test_send_and_disconnect_refused_while_streaming():
    backend = Backend()
    session = Session({"memory": backend.factory})
    try:
        _connect(session)
        backend.stop_fake()
        session.submit({"cmd": "stream", "params": {"confirmed": True, "lines": ["G0 X1", "G0 Y2"]}})
        assert wait_state(session, "streaming", timeout=5.0)
        # Rejected at submission time, never queued behind the stream.
        session.submit({"cmd": "send", "params": {"line": "G0 X9"}})
        session.submit({"cmd": "disconnect"})
        session.submit({"cmd": "stream", "params": {"confirmed": True, "lines": ["G0 X1"]}})
        codes = [e["code"] for e in session.events if e.get("event") == "error"]
        assert codes.count("busy_streaming") == 3
        session.worker.cancel()
        session.wait_event("stream_done", timeout=5.0)
        assert wait_state(session, "connected")
        assert session.worker.state == "connected"
    finally:
        backend.cleanup()
        session.shutdown()


def test_status_allowed_while_streaming():
    backend = Backend()
    session = Session({"memory": backend.factory})
    try:
        _connect(session)
        session.submit({"cmd": "send", "params": {"line": "G0 X5"}})
        session.wait_event("response")
        backend.stop_fake()
        session.submit({"cmd": "stream", "params": {"confirmed": True, "lines": ["G0 X1", "G0 Y2"]}})
        assert wait_state(session, "streaming", timeout=5.0)
        session.submit({"cmd": "status"})
        session.worker.cancel()
        session.wait_event("stream_done", timeout=5.0)
        # status was never rejected as busy (it may then simply time out
        # against the silent link, which is fine).
        errors = [e for e in session.events if e.get("event") == "error"]
        assert not any(e["code"] == "busy_streaming" for e in errors)
    finally:
        backend.cleanup()
        session.shutdown()
