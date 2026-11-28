"""Connection manager: handshake, line exchange, status polling, streaming.

Pure Python, on top of a Transport and the character-counting streamer.
"""

from freecad.cnc_control.core.grbl_protocol import (
    CMD_STATUS_QUERY,
    Alarm,
    Error,
    Ok,
    Setting,
    StatusReport,
    Welcome,
    parse_line,
)
from freecad.cnc_control.core.streamer import CharacterCountingStreamer, StreamResult


class GrblConnection:
    """One controller connection: handshake, commands, status, streaming."""

    def __init__(self, transport) -> None:
        self._transport = transport
        self._version: str | None = None
        self.last_status: StatusReport | None = None

    @property
    def version(self) -> str | None:
        """GRBL version reported by the welcome banner, once connected."""
        return self._version

    def connect(self, timeout: float = 10.0) -> str:
        """Read the welcome banner; returns the version string."""
        while True:
            line = self._transport.read_line(timeout=timeout)
            if line is None:
                raise ConnectionError("transport closed before the welcome message")
            parsed = parse_line(line)
            if isinstance(parsed, Welcome):
                self._version = parsed.version
                return parsed.version
            # Anything before the banner is ignored.

    def close(self) -> None:
        self._transport.close()

    def send_line(self, line: str, timeout: float = 10.0) -> Ok | Error | Alarm:
        """Send one line and wait for its own ok/error/ALARM response."""
        self._transport.write_line(line)
        while True:
            response = self._transport.read_line(timeout=timeout)
            if response is None:
                raise ConnectionError("transport closed while waiting for a response")
            parsed = parse_line(response)
            if isinstance(parsed, (Ok, Error, Alarm)):
                return parsed
            # Push messages are not responses to this line.

    def poll_status(self, timeout: float = 2.0) -> StatusReport:
        """Send the real-time status query and parse the report."""
        self._transport.write(CMD_STATUS_QUERY)
        while True:
            line = self._transport.read_line(timeout=timeout)
            if line is None:
                raise ConnectionError("transport closed while waiting for status")
            parsed = parse_line(line)
            if isinstance(parsed, StatusReport):
                self.last_status = parsed
                return parsed
            # Skip push messages that arrive first.

    def read_settings(self, timeout: float = 10.0) -> dict[str, float]:
        """Read ``$$`` settings as a code-to-value mapping."""
        self._transport.write_line("$$")
        settings: dict[str, float] = {}
        while True:
            line = self._transport.read_line(timeout=timeout)
            if line is None:
                raise ConnectionError("transport closed while reading settings")
            parsed = parse_line(line)
            if isinstance(parsed, Setting):
                try:
                    settings[parsed.code] = float(parsed.value)
                except ValueError:
                    continue
            elif isinstance(parsed, (Ok, Error, Alarm)):
                if isinstance(parsed, Ok):
                    return settings
                raise ConnectionError(f"$$ rejected: {parsed}")

    def stream(self, lines, stop_event=None) -> StreamResult:
        """Stream G-code lines with character counting (see core/streamer.py)."""
        return CharacterCountingStreamer(self._transport).run(lines, stop_event)
