"""GrblConnection tests against the fake GRBL over the in-memory transport."""

import threading

from freecad.cnc_control.core.connection import GrblConnection
from freecad.cnc_control.core.grbl_protocol import Alarm, Error, Ok, StatusReport
from freecad.cnc_control.core.transport import MemoryTransport
from freecad.cnc_control.testing.fake_grbl import FakeGrbl


class Conversation:
    """Fake GRBL served on one end of a memory pair."""

    def __init__(self) -> None:
        controller, client = MemoryTransport.pair()
        self.controller = controller
        self.client = client
        self.fake = FakeGrbl()
        self.stop = threading.Event()
        threading.Thread(
            target=self.fake.serve, args=(controller, self.stop), daemon=True
        ).start()

    def connect(self) -> GrblConnection:
        connection = GrblConnection(self.client)
        connection.connect()
        return connection

    def cleanup(self) -> None:
        self.stop.set()


def test_connect_reads_version():
    conv = Conversation()
    try:
        connection = conv.connect()
        assert connection.version == "1.1h"
    finally:
        conv.cleanup()


def test_send_line_ok():
    conv = Conversation()
    try:
        connection = conv.connect()
        assert isinstance(connection.send_line("G0 X1"), Ok)
    finally:
        conv.cleanup()


def test_send_line_error():
    conv = Conversation()
    try:
        connection = conv.connect()
        conv.fake.inject_error(33)
        result = connection.send_line("G0 X999999")
        assert isinstance(result, Error)
        assert result.code == 33
    finally:
        conv.cleanup()


def test_send_line_alarm():
    conv = Conversation()
    try:
        connection = conv.connect()
        conv.fake.inject_alarm(2)
        result = connection.send_line("G0 X1")
        assert isinstance(result, Alarm)
        assert result.code == 2
    finally:
        conv.cleanup()


def test_poll_status_idle():
    conv = Conversation()
    try:
        connection = conv.connect()
        status = connection.poll_status()
        assert isinstance(status, StatusReport)
        assert status.state == "Idle"
        assert status.mpos == (0.0, 0.0, 0.0)
        assert connection.last_status is status
    finally:
        conv.cleanup()


def test_poll_status_after_motion():
    conv = Conversation()
    try:
        connection = conv.connect()
        connection.send_line("G0 X5 Y7")
        status = connection.poll_status()
        assert status.state == "Run"
        assert status.mpos == (5.0, 7.0, 0.0)
    finally:
        conv.cleanup()


def test_stream_over_connection():
    conv = Conversation()
    try:
        connection = conv.connect()
        result = connection.stream(["G0 X1", "G0 Y2", "G0 Z3"])
        assert result.completed
        assert result.acked == 3
    finally:
        conv.cleanup()


def test_read_settings_from_dollar_dollar():
    conv = Conversation()
    try:
        connection = conv.connect()
        settings = connection.read_settings()
        assert settings["130"] == 200.0
        assert settings["100"] == 250.0
    finally:
        conv.cleanup()


def test_work_offset_comes_from_the_status_report():
    conv = Conversation()
    try:
        conv.fake.set_work_offset((190.0, -5.0, 0.0))
        connection = conv.connect()
        assert connection.work_offset() == (190.0, -5.0, 0.0)
    finally:
        conv.cleanup()


def test_close():
    conv = Conversation()
    try:
        connection = conv.connect()
        connection.close()
        assert conv.client.is_closed
    finally:
        conv.cleanup()


def test_connect_on_closed_transport_raises():
    _controller, client = MemoryTransport.pair()
    client.close()
    connection = GrblConnection(client)
    try:
        connection.connect()
        raised = False
    except ConnectionError:
        raised = True
    assert raised


def test_send_line_timeout_on_silent_link():
    _controller, client = MemoryTransport.pair()  # no server: never answers
    connection = GrblConnection(client)
    try:
        connection.send_line("G0 X1", timeout=0.2)
        raised = False
    except TimeoutError:
        raised = True
    assert raised


def test_poll_status_timeout_on_silent_link():
    _controller, client = MemoryTransport.pair()
    connection = GrblConnection(client)
    try:
        connection.poll_status(timeout=0.2)
        raised = False
    except TimeoutError:
        raised = True
    assert raised
