"""Out-of-band real-time bytes and explicit jog steps in the worker."""

import time

from freecad.cnc_control.core.transport import MemoryTransport, Transport
from tests.core.test_worker import Backend, Session


class RecordingTransport(Transport):
    """Delegate a transport while recording every raw write."""

    def __init__(self, inner) -> None:
        super().__init__()
        self.inner = inner
        self.writes: list[bytes] = []

    def write(self, data: bytes) -> None:
        self.writes.append(bytes(data))
        self.inner.write(data)

    def read(self) -> bytes | None:
        return self.inner.read()

    def close(self) -> None:
        super().close()
        self.inner.close()


class RecordingBackend(Backend):
    """Backend whose client transport records raw writes."""

    def __init__(self) -> None:
        super().__init__()
        self.recorder: RecordingTransport | None = None

    def factory(self, _params):
        controller, client = MemoryTransport.pair()
        self.peer = controller
        self.recorder = RecordingTransport(client)
        self.start_fake()
        return self.recorder


def connect(session) -> None:
    session.submit({"cmd": "connect", "params": {"kind": "memory"}})
    assert session.wait_event("connected") is not None


def wait_error(session, code: str, timeout: float = 2.0):
    deadline = time.time() + timeout
    while time.time() < deadline:
        for event in session.events:
            if event.get("event") == "error" and event.get("code") == code:
                return event
        time.sleep(0.01)
    return None


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


def test_realtime_command_is_written_from_the_worker_thread():
    backend = RecordingBackend()
    session = Session({"memory": backend.factory})
    try:
        connect(session)
        session.submit({"cmd": "realtime", "params": {"command": "hold"}})
        event = session.wait_event("realtime")
        assert event is not None and event["command"] == "hold"
        assert backend.recorder is not None
        assert b"!" in backend.recorder.writes
    finally:
        backend.cleanup()
        session.shutdown()


def test_realtime_command_bypasses_a_running_stream():
    backend = RecordingBackend()
    session = Session({"memory": backend.factory})
    try:
        connect(session)
        session.approve(["G0 X1"])
        backend.fake.silence_motion()
        session.submit({"cmd": "stream", "params": {"confirmed": True, "lines": ["G0 X1"]}})
        assert wait_state(session, "streaming")
        session.submit({"cmd": "realtime", "params": {"command": "hold"}})
        event = session.wait_event("realtime")
        assert event is not None and event["command"] == "hold"
        assert backend.recorder is not None
        assert b"!" in backend.recorder.writes
        session.worker.cancel()
        assert session.wait_event("stream_done") is not None
    finally:
        backend.cleanup()
        session.shutdown()


def test_unknown_realtime_command_is_rejected():
    backend = RecordingBackend()
    session = Session({"memory": backend.factory})
    try:
        connect(session)
        session.submit({"cmd": "realtime", "params": {"command": "dance"}})
        assert wait_error(session, "invalid_command") is not None
        assert backend.recorder is not None
        assert backend.recorder.writes == []
    finally:
        backend.cleanup()
        session.shutdown()


def test_jog_step_sends_a_jog_line_and_moves_the_fake():
    backend = RecordingBackend()
    session = Session({"memory": backend.factory})
    try:
        connect(session)
        session.submit(
            {"cmd": "jog", "params": {"axis": "X", "distance": 5, "feed": 100}}
        )
        event = session.wait_event("jog")
        assert event is not None
        assert event["line"] == "$J=G91 X5 F100"
        response = session.wait_event("response")
        assert response is not None and response["kind"] == "ok"
        assert backend.fake._mpos == (5.0, 0.0, 0.0)
    finally:
        backend.cleanup()
        session.shutdown()


def test_jog_is_refused_while_the_controller_is_in_alarm():
    backend = RecordingBackend()
    session = Session({"memory": backend.factory})
    try:
        connect(session)
        backend.fake.inject_alarm(1)
        session.submit(
            {"cmd": "jog", "params": {"axis": "X", "distance": 5, "feed": 100}}
        )
        assert wait_error(session, "alarm_active") is not None
        time.sleep(0.1)
        assert not any(event.get("event") == "jog" for event in session.events)
    finally:
        backend.cleanup()
        session.shutdown()


def test_jog_rejects_invalid_parameters():
    backend = RecordingBackend()
    session = Session({"memory": backend.factory})
    try:
        connect(session)
        params = {"axis": "X", "distance": 5, "feed": 0}
        session.submit({"cmd": "jog", "params": params})
        assert wait_error(session, "invalid_command") is not None
    finally:
        backend.cleanup()
        session.shutdown()
