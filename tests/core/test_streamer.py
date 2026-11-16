"""Streamer tests against the fake GRBL over the in-memory transport."""

import threading

from freecad.cnc_control.core.streamer import RX_BUFFER_SIZE, CharacterCountingStreamer
from freecad.cnc_control.core.transport import MemoryTransport
from freecad.cnc_control.testing.fake_grbl import FakeGrbl


class Conversation:
    """Fake GRBL served on one end of a memory pair; helper for tests."""

    def __init__(self) -> None:
        controller, client = MemoryTransport.pair()
        self.controller = controller
        self.client = client
        self.fake = FakeGrbl()
        self.stop = threading.Event()
        self.thread = threading.Thread(
            target=self.fake.serve, args=(controller, self.stop), daemon=True
        )
        self.thread.start()

    def result_for(self, lines):
        return CharacterCountingStreamer(self.client).run(lines)

    def cleanup(self) -> None:
        self.stop.set()


def test_empty_program():
    conv = Conversation()
    try:
        result = conv.result_for([])
        assert result.sent == 0
        assert result.completed
    finally:
        conv.cleanup()


def test_short_program_all_acked():
    conv = Conversation()
    try:
        result = conv.result_for(["G0 X1", "G0 Y2", "G0 Z3"])
        assert result.sent == 3
        assert result.acked == 3
        assert result.completed
        assert result.errors == []
        assert result.alarms == []
    finally:
        conv.cleanup()


def test_long_program_respects_buffer():
    conv = Conversation()
    try:
        lines = [f"G1 X{i} F100" for i in range(1, 101)]
        result = conv.result_for(lines)
        assert result.sent == 100
        assert result.acked == 100
        assert result.completed
    finally:
        conv.cleanup()


def test_error_stops_stream_and_drains():
    conv = Conversation()
    try:
        lines = [f"G1 X{i} F100" for i in range(1, 11)]
        conv.fake.inject_error(33)
        result = conv.result_for(lines)
        assert len(result.errors) == 1
        assert result.errors[0].code == 33
        assert not result.completed
        # Character counting may send several lines before the error is read,
        # but never past the buffer; every sent line gets a response.
        assert result.sent <= len(lines)
        assert result.acked + len(result.errors) == result.sent
    finally:
        conv.cleanup()


def test_alarm_aborts_stream():
    conv = Conversation()
    try:
        lines = [f"G1 X{i} F100" for i in range(1, 11)]
        conv.fake.inject_alarm(1)
        result = conv.result_for(lines)
        assert len(result.alarms) == 1
        assert result.alarms[0].code == 1
        assert not result.completed
    finally:
        conv.cleanup()


def test_inflight_returns_to_zero():
    conv = Conversation()
    try:
        result = conv.result_for(["G0 X1", "G0 Y2"])
        assert result.completed
        assert conv.client is not None
        streamer = CharacterCountingStreamer(conv.client)
        streamer.run(["G0 X1"])
        assert streamer.inflight_bytes == 0
    finally:
        conv.cleanup()


def test_realtime_write_goes_through():
    conv = Conversation()
    try:
        streamer = CharacterCountingStreamer(conv.client)
        streamer.write_realtime(b"!")
        assert conv.controller.read() == b"!"
    finally:
        conv.cleanup()


def test_line_too_long_never_sent():
    conv = Conversation()
    try:
        lines = ["G1 X1 F100", "G1 " + "X1" * 200]  # second exceeds 128 bytes
        result = conv.result_for(lines)
        assert result.sent == 1
        assert not result.completed
    finally:
        conv.cleanup()


def test_push_messages_do_not_acknowledge():
    conv = Conversation()
    try:
        # The banner arrives before any ok; it must not release a line.
        result = conv.result_for(["G0 X1", "G0 Y2"])
        assert result.acked == 2
        assert result.completed
    finally:
        conv.cleanup()


def test_rx_buffer_size_constant():
    assert RX_BUFFER_SIZE == 128
