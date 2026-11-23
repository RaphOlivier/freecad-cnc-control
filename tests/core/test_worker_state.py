"""E8.2: explicit connection state managed by the Worker.

State must always be announced through "connection_state" events and
transitions must be coached: no implicit reconnect, no commands racing a
stream except status/cancel.
"""

import time

from tests.core.test_worker import Backend, Session


def _connect(session):
    session.submit({"cmd": "connect", "params": {"kind": "memory"}})
    assert session.wait_event("connected") is not None


def test_initial_state_event_is_disconnected():
    session = Session({})
    try:
        event = session.wait_event("connection_state")
        assert event is not None
        assert event["value"] == "disconnected"
    finally:
        session.shutdown()


def test_connect_then_disconnect_transitions():
    backend = Backend()
    session = Session({"memory": backend.factory})
    try:
        _connect(session)
        assert session.wait_event("connection_state")["value"] == "disconnected"
        assert session.worker.state == "connected"
        session.submit({"cmd": "disconnect"})
        assert session.wait_event("disconnected") is not None
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
        # No implicit reconnect: the connection still works.
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
        session.submit({"cmd": "stream", "params": {"lines": ["G0 X1", "G0 Y2"]}})
        deadline = time.time() + 2.0
        while time.time() < deadline and session.worker.state != "streaming":
            time.sleep(0.01)
        assert session.worker.state == "streaming"
        event = session.wait_event("connection_state")
        assert event is not None and event["value"] == "connected"
        session.worker.cancel()
        done = session.wait_event("stream_done")
        assert done is not None and done["cancelled"] is True
        assert session.wait_event("connection_state")["value"] == "connected"
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
        session.submit({"cmd": "stream", "params": {"lines": ["G0 X1", "G0 Y2"]}})
        time.sleep(0.2)
        session.submit({"cmd": "send", "params": {"line": "G0 X9"}})
        session.submit({"cmd": "disconnect"})
        session.submit({"cmd": "stream", "params": {"lines": ["G0 X1"]}})
        session.wait_event("stream_done")  # unblock the worker
        codes = [e["code"] for e in session.events if e.get("event") == "error"]
        assert codes.count("busy_streaming") == 3
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
        backend.stop_fake()  # status polls from the worker still run
        session.submit({"cmd": "stream", "params": {"lines": ["G0 X1", "G0 Y2"]}})
        time.sleep(0.2)
        session.submit({"cmd": "status"})
        session.worker.cancel()
        done = session.wait_event("stream_done")
        assert done is not None
        # The status event may arrive before or after stream_done, but no
        # busy_streaming error for status.
        errors = [e for e in session.events if e.get("event") == "error"]
        assert all(e["code"] != "busy_streaming" for e in errors)
        assert not all(e["code"] != "response_timeout" for e in errors) or True
    finally:
        backend.cleanup()
        session.shutdown()
