"""E8: worker preflight gate, confirmation, cancellation and check mode."""

import time

from tests.core.test_worker import Backend, Session


def connect(session) -> None:
    session.submit({"cmd": "connect", "params": {"kind": "memory"}})
    assert session.wait_event("connected") is not None


def approve(session, lines) -> None:
    session.submit({"cmd": "preflight", "params": {"lines": lines}})
    event = session.wait_event("preflight")
    assert event is not None and event["accepted"] is True


def wait_state(session, value: str, timeout: float = 2.0) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        for event in session.events:
            if (
                event.get("event") == "connection_state"
                and event.get("value") == value
            ):
                return True
        time.sleep(0.01)
    return False


def test_stream_without_preflight_is_rejected():
    backend = Backend()
    session = Session({"memory": backend.factory})
    try:
        connect(session)
        session.submit(
            {"cmd": "stream", "params": {"confirmed": True, "lines": ["G0 X1"]}}
        )
        event = session.wait_event("error")
        assert event is not None and event["code"] == "preflight_required"
        assert not any(e.get("event") == "stream_done" for e in session.events)
    finally:
        backend.cleanup()
        session.shutdown()


def test_non_boolean_stream_flags_are_rejected():
    backend = Backend()
    session = Session({"memory": backend.factory})
    try:
        connect(session)
        session.submit(
            {"cmd": "stream", "params": {"lines": ["G0 X1"], "check_mode": "false"}}
        )
        assert wait_error(session, "invalid_command") is not None
    finally:
        backend.cleanup()
        session.shutdown()


def test_real_stream_requires_explicit_confirmation():
    backend = Backend()
    session = Session({"memory": backend.factory})
    try:
        connect(session)
        approve(session, ["G0 X1"])
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
        assert event["work_offset"] == [0.0, 0.0, 0.0]
        assert not any(e.get("event") == "stream_done" for e in session.events)
    finally:
        backend.cleanup()
        session.shutdown()


def test_preflight_refuses_out_of_limits_and_blocks_stream():
    backend = Backend()
    session = Session({"memory": backend.factory})
    try:
        connect(session)
        lines = ["G21 G90", "G1 X300"]
        session.submit({"cmd": "preflight", "params": {"lines": lines}})
        event = session.wait_event("preflight")
        assert event is not None
        assert event["accepted"] is False
        assert any("X travel 300" in reason for reason in event["reasons"])
        session.submit(
            {"cmd": "stream", "params": {"confirmed": True, "lines": lines}}
        )
        error = wait_error(session, "preflight_rejected")
        assert error is not None
        assert not any(e.get("event") == "stream_done" for e in session.events)
    finally:
        backend.cleanup()
        session.shutdown()


def wait_error(session, code: str, timeout: float = 2.0):
    deadline = time.time() + timeout
    while time.time() < deadline:
        for event in session.events:
            if event.get("event") == "error" and event.get("code") == code:
                return event
        time.sleep(0.01)
    return None


def test_worker_applies_work_offset_from_status():
    backend = Backend()
    backend.fake.set_work_offset((190.0, 0.0, 0.0))
    session = Session({"memory": backend.factory})
    try:
        connect(session)
        session.submit(
            {
                "cmd": "preflight",
                "params": {"lines": ["G21 G90", "G1 X20"]},
            }
        )
        event = session.wait_event("preflight")
        assert event is not None
        assert event["accepted"] is False
        assert event["work_offset"] == [190.0, 0.0, 0.0]
        assert any("X travel 210" in reason for reason in event["reasons"])
    finally:
        backend.cleanup()
        session.shutdown()


def test_injected_system_line_is_never_streamed():
    backend = Backend()
    session = Session({"memory": backend.factory})
    try:
        connect(session)
        lines = ["$C", "G0 X123"]
        session.submit({"cmd": "preflight", "params": {"lines": lines}})
        assert wait_error(session, "invalid_job_lines") is not None
        session.submit(
            {"cmd": "stream", "params": {"confirmed": True, "lines": lines}}
        )
        assert wait_error(session, "preflight_required") is not None
        assert backend.fake._mpos == (0.0, 0.0, 0.0)
    finally:
        backend.cleanup()
        session.shutdown()


def test_early_cancel_is_latched_until_the_stream_starts():
    backend = Backend()
    session = Session({"memory": backend.factory})
    try:
        connect(session)
        approve(session, ["G0 X1"])
        backend.fake.silence_motion()
        session.worker.cancel()  # before the stream handler runs
        session.submit(
            {"cmd": "stream", "params": {"confirmed": True, "lines": ["G0 X1"]}}
        )
        done = session.wait_event("stream_done")
        assert done is not None
        assert done["cancelled"] is True
        assert done["sent"] == 0
    finally:
        backend.cleanup()
        session.shutdown()


def test_shutdown_during_stream_cancels_and_announces_bye():
    backend = Backend()
    session = Session({"memory": backend.factory})
    try:
        connect(session)
        approve(session, ["G0 X1"])
        backend.fake.silence_motion()
        session.submit(
            {"cmd": "stream", "params": {"confirmed": True, "lines": ["G0 X1"]}}
        )
        assert wait_state(session, "streaming", timeout=5.0)
        session.submit({"cmd": "shutdown"})
        done = session.wait_event("stream_done", timeout=5.0)
        assert done is not None and done["cancelled"] is True
        assert session.wait_event("bye") is not None
        session.thread.join(timeout=2.0)
        assert not session.thread.is_alive()
    finally:
        backend.cleanup()


def test_check_mode_stream_toggles_check_mode_without_confirmation():
    backend = Backend()
    session = Session({"memory": backend.factory})
    try:
        connect(session)
        approve(session, ["G0 X1"])
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


def test_check_mode_off_failure_is_reported():
    backend = Backend()
    session = Session({"memory": backend.factory})
    try:
        connect(session)
        approve(session, ["G0 X1"])
        backend.fake.fail_check_mode_off()
        session.submit(
            {"cmd": "stream", "params": {"lines": ["G0 X1"], "check_mode": True}}
        )
        assert session.wait_event("stream_done") is not None
        assert wait_error(session, "check_mode_off_failed") is not None
        toggles = [e for e in session.events if e.get("event") == "check_mode"]
        assert [e["enabled"] for e in toggles] == [True]
    finally:
        backend.cleanup()
        session.shutdown()
