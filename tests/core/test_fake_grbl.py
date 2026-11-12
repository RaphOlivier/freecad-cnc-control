"""Fake GRBL conversations over the in-memory transport."""

import threading

from freecad.cnc_control.core.transport import MemoryTransport
from freecad.cnc_control.testing.fake_grbl import DEFAULT_SETTINGS, FakeGrbl


def make_conversation():
    controller, client = MemoryTransport.pair()
    fake = FakeGrbl()
    stop = threading.Event()
    thread = threading.Thread(target=fake.serve, args=(controller, stop), daemon=True)
    thread.start()
    return fake, client, stop


def test_banner_and_motion_conversation():
    _fake, client, stop = make_conversation()
    try:
        assert client.read_line() == "Grbl 1.1h ['$' for help]"
        client.write_line("G0 X10")
        assert client.read_line() == "ok"
        client.write_line("G0 Y5")
        assert client.read_line() == "ok"
        client.write(b"?")
        status = client.read_line()
        assert status.startswith("<Run|MPos:10.000,5.000,0.000|WCO:0.000,0.000,0.000")
    finally:
        stop.set()


def test_feed_hold_and_resume():
    _fake, client, stop = make_conversation()
    try:
        assert client.read_line() == "Grbl 1.1h ['$' for help]"
        client.write_line("G1 X50 F100")
        assert client.read_line() == "ok"
        client.write(b"!")
        client.write(b"?")
        assert client.read_line().startswith("<Hold|")
        client.write(b"~")
        client.write(b"?")
        assert client.read_line().startswith("<Idle|")
    finally:
        stop.set()


def test_soft_reset_resends_banner():
    _fake, client, stop = make_conversation()
    try:
        assert client.read_line() == "Grbl 1.1h ['$' for help]"
        client.write(b"\x18")
        assert client.read_line() == "Grbl 1.1h ['$' for help]"
    finally:
        stop.set()


def test_settings_query():
    _fake, client, stop = make_conversation()
    try:
        assert client.read_line() == "Grbl 1.1h ['$' for help]"
        client.write_line("$$")
        lines = [client.read_line() for _ in range(len(DEFAULT_SETTINGS) + 1)]
        assert lines[0] == "$0=10"
        assert lines[-1] == "ok"
        assert len(lines) == len(DEFAULT_SETTINGS) + 1
    finally:
        stop.set()


def test_injected_alarm_stops_gcode_until_unlock():
    fake, client, stop = make_conversation()
    try:
        assert client.read_line() == "Grbl 1.1h ['$' for help]"
        fake.inject_alarm(1)
        client.write_line("G0 X1")
        assert client.read_line() == "ALARM:1"
        client.write_line("G0 X2")
        assert client.read_line() == "error:9"
        client.write_line("$X")
        assert client.read_line() == "ok"
        client.write_line("G0 X3")
        assert client.read_line() == "ok"
    finally:
        stop.set()


def test_injected_error():
    fake, client, stop = make_conversation()
    try:
        assert client.read_line() == "Grbl 1.1h ['$' for help]"
        fake.inject_error(33)
        client.write_line("G0 X999999")
        assert client.read_line() == "error:33"
        client.write_line("G0 X1")
        assert client.read_line() == "ok"
    finally:
        stop.set()


def test_check_mode():
    _fake, client, stop = make_conversation()
    try:
        assert client.read_line() == "Grbl 1.1h ['$' for help]"
        client.write_line("$C")
        assert client.read_line() == "ok"
        client.write_line("G0 X1000")
        assert client.read_line() == "ok"
        client.write(b"?")
        assert client.read_line().startswith("<Idle|")  # no motion in check mode
    finally:
        stop.set()
