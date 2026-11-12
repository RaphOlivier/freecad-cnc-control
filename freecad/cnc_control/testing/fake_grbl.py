"""A fake GRBL 1.1 controller in pure Python, for tests on all platforms.

Behavior follows the official GRBL 1.1 documentation (same sources as
core/grbl_protocol.py). It implements the subset needed by the milestone-1
tests: welcome banner, ok/error responses, status reports, $$ settings,
$G, $C check mode, $X, $H, feed hold/resume, soft reset, jog cancel, and
injectable errors/alarms. Unsolicited ALARM messages are delivered with the
next line's response (test-friendly approximation of asynchronous push).
"""

import os
import re
import select
import threading

from freecad.cnc_control.core.grbl_protocol import CMD_JOG_CANCEL, CMD_SOFT_RESET

DEFAULT_SETTINGS = {
    "0": "10", "1": "25", "2": "0", "3": "0", "4": "0", "5": "0", "6": "0",
    "10": "255", "11": "0.010", "12": "0.002", "13": "0", "20": "0", "21": "0",
    "22": "0", "23": "0", "24": "25.000", "25": "500.000", "26": "250",
    "27": "1.000", "30": "1000", "31": "0", "32": "0", "100": "250.000",
    "101": "250.000", "102": "250.000", "110": "500.000", "111": "500.000",
    "112": "500.000", "120": "10.000", "121": "10.000", "122": "10.000",
    "130": "200.000", "131": "200.000", "132": "200.000",
}

REALTIME_BYTES = frozenset({ord("?"), ord("!"), ord("~"), CMD_SOFT_RESET[0], CMD_JOG_CANCEL[0]})
HELP_LINE = "[HLP:$$ $# $G $I $N $x=val $Nx=line $J=line $SLP $C $X $H ~ ! ? ctrl-x]"
_AXIS_RE = re.compile(r"([XYZ])(-?\d+(?:\.\d+)?)")


class FakeGrbl:
    """Scriptable GRBL 1.1 emulator over any byte stream."""

    def __init__(self, version: str = "1.1h") -> None:
        self.version = version
        self._line_buffer = bytearray()
        self._state = "Idle"
        self._mpos = (0.0, 0.0, 0.0)
        self._wco = (0.0, 0.0, 0.0)
        self._check_mode = False
        self._settings = dict(DEFAULT_SETTINGS)
        self._error_queue: list[int] = []
        self._alarm_queue: list[int] = []

    # ----- test controls -------------------------------------------------
    def inject_error(self, code: int) -> None:
        """Make the next line's response an error:x."""
        self._error_queue.append(code)

    def inject_alarm(self, code: int) -> None:
        """Deliver ALARM:x with the next response and lock G-code."""
        self._alarm_queue.append(code)
        self._state = "Alarm"

    # ----- protocol --------------------------------------------------------
    @property
    def banner(self) -> bytes:
        return f"Grbl {self.version} ['$' for help]\r\n".encode()

    def process(self, data: bytes) -> bytes:
        """Feed raw bytes (lines and/or real-time bytes); return the reply."""
        out = bytearray()
        for byte in data:
            if byte in REALTIME_BYTES:
                out += self._realtime(byte)
            elif byte == 0x0A:
                out += self._handle_line(self._line_buffer.decode(errors="replace"))
                self._line_buffer = bytearray()
            elif byte == 0x0D:
                continue
            else:
                self._line_buffer.append(byte)
        return bytes(out)

    def serve(self, transport, stop_event: threading.Event | None = None) -> None:
        """Serve the fake GRBL over a Transport until stopped or closed."""
        stop = stop_event if stop_event is not None else threading.Event()
        transport.write(self.banner)
        while not stop.is_set():
            data = transport.read()
            if data is None:
                return
            out = self.process(data)
            if out:
                transport.write(out)

    def serve_fd(self, fd: int, stop_event: threading.Event | None = None) -> None:
        """Serve the fake GRBL on a raw file descriptor (pty slave)."""
        stop = stop_event if stop_event is not None else threading.Event()
        os.write(fd, self.banner)
        while not stop.is_set():
            ready, _, _ = select.select([fd], [], [], 0.05)
            if not ready:
                continue
            try:
                data = os.read(fd, 4096)
            except OSError:
                return
            if not data:
                return
            out = self.process(data)
            if out:
                os.write(fd, out)

    def _realtime(self, byte: int) -> bytes:
        if byte == ord("?"):
            return self._status().encode()
        if byte == ord("!"):
            if self._state == "Run":
                self._state = "Hold"
            return b""
        if byte == ord("~"):
            if self._state == "Hold":
                self._state = "Idle"
            return b""
        if byte == CMD_SOFT_RESET[0]:
            self._state = "Idle"
            self._line_buffer = bytearray()
            self._check_mode = False
            return self.banner
        if byte == CMD_JOG_CANCEL[0]:
            if self._state == "Jog":
                self._state = "Idle"
            return b""
        return b""

    def _status(self) -> str:
        mpos = ",".join(f"{value:.3f}" for value in self._mpos)
        wco = ",".join(f"{value:.3f}" for value in self._wco)
        return f"<{self._state}|MPos:{mpos}|WCO:{wco}|FS:0.0,0>\r\n"

    def _handle_line(self, line: str) -> bytes:
        text = line.strip()
        if not text:
            return b""
        if self._alarm_queue:
            code = self._alarm_queue.pop(0)
            return f"ALARM:{code}\r\n".encode()
        if self._error_queue:
            code = self._error_queue.pop(0)
            return f"error:{code}\r\n".encode()
        if text == "$$":
            lines = [f"${code}={value}" for code, value in self._settings.items()]
            return ("\r\n".join(lines) + "\r\nok\r\n").encode()
        if text == "$G":
            return b"[GC:G0 G54 G17 G21 G90 G94 M0 M5 M9 T0 S0.0 F0.0]\r\nok\r\n"
        if text == "$":
            return (HELP_LINE + "\r\nok\r\n").encode()
        if text == "$H":
            self._state = "Idle"
            return b"ok\r\n"
        if text == "$X":
            if self._state == "Alarm":
                self._state = "Idle"
            return b"ok\r\n"
        if text == "$C":
            self._check_mode = not self._check_mode
            return b"ok\r\n"
        if text.startswith("$"):
            return b"error:3\r\n"
        if self._state == "Alarm":
            return b"error:9\r\n"
        self._apply_motion(text)
        return b"ok\r\n"

    def _apply_motion(self, text: str) -> None:
        if self._check_mode:
            return
        upper = text.upper()
        if not upper.startswith(("G0", "G1")):
            return
        self._state = "Run"
        coords = {match.group(1): float(match.group(2)) for match in _AXIS_RE.finditer(upper)}
        x, y, z = self._mpos
        self._mpos = (coords.get("X", x), coords.get("Y", y), coords.get("Z", z))
