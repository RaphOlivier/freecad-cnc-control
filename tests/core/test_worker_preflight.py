"""E8: worker preflight events, confirmation gate and GRBL check mode."""

import time

from tests.core.test_worker import Backend, Session


def connect(session) -> None:
    session.submit({"cmd": "connect", "params": {"kind": "memory"}})
    assert session.wait_event("connected") is not None


def wait_for(session, predicate, timeout: float = 2.0):
    deadline = time.time() + timeout
    while time.time() < deadline:
        for event in session.events:
            if predicate(event):
                return event
        time.sleep(0.01)
    return None


def test_real_stream_requires_explicit_confirmation():
    backend = Backend()
    session = Session({"memory": backend.factory})
    try:
        connect(session)
        session.submit({"cmd": "stream", "params": {"lines": ["G0 X1"]}})
        event = session.wait_event("error")
        assert event is not None and event["code"] == "confirmation_required"
        time.sleep(0.1)
        assert not any(e.get("event") == "stream_done" for e in session.events)
    finally:
        backend.cleanup()
        session.shutdown()


def test_preflight_reports_limits_without_starting_a_job():
    backend = Backend()
    session = Session({"memory": backend.factory})
    try:
        connect(session)
        session.submit(
            {"cmd": "preflight", "params": {"lines": ["G21 G90", "G1 X10 Y10"]}}
        )
        event = session.wait_event("preflight")
        assert event is not None
        assert event["accepted"] is True
        assert event["requires_confirmation"] is True
        assert event["suggest_check_mode"] is True
        assert event["limits"]["travel"] == [200.0, 200.0, 200.0]
        assert event["bounds"]["x"] == [0.0, 10.0]
        assert not any(e.get("event") == "stream_done" for e in session.events)
    finally:
        backend.cleanup()
        session.shutdown()


def test_preflight_refuses_out_of_limits():
    backend = Backend()
    session = Session({"memory": backend.factory})
    try:
        connect(session)
        session.submit({"cmd": "preflight", "params": {"lines": ["G21 G90", "G1 X300"]}})
        event = session.wait_event("preflight")
        assert event is not None
        assert event["accepted"] is False
        assert any("X travel 300" in reason for reason in event["reasons"])
    finally:
        backend.cleanup()
        session.shutdown()


def test_check_mode_stream_toggles_check_mode_without_confirmation():
    backend = Backend()
    session = Session({"memory": backend.factory})
    try:
        connect(session)
        session.submit(
            {"cmd": "stream", "params": {"lines": ["G0 X1"], "check_mode": True}}
        )
        done = session.wait_event("stream_done")
        assert done is not None
        assert done["check_mode"] is True
        assert done["completed"] is True
        toggles = [e for e in session.events if e.get("event") == "check_mode"]
        assert [e["enabled"] for e in toggles] == [True, False]
        assert not any(e.get("code") == "confirmation_required" for e in session.events)
    finally:
        backend.cleanup()
        session.shutdown()
