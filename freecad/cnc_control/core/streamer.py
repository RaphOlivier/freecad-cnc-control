"""Character-counting G-code streamer for GRBL 1.1.

Sends lines while the bytes in flight fit in GRBL's serial RX buffer
(128 bytes per the official documentation), tracks one pending length per
sent line, and releases it on each ok/error response. Push messages
(banner, [MSG:...], status reports) never acknowledge a line. Any error:
stops sending, then remaining in-flight acknowledgements are drained; any
ALARM: aborts immediately. A line that can never fit the buffer is never
sent and ends the stream incomplete.

Sources: https://github.com/gnea/grbl/wiki/Grbl-v1.1-Interface (streaming
protocols section).
"""

import threading
from collections import deque
from dataclasses import dataclass, field

from freecad.cnc_control.core.grbl_protocol import Alarm, Error, Ok, parse_line

RX_BUFFER_SIZE = 128  # GRBL serial receive buffer, bytes (Interface wiki)


@dataclass
class StreamResult:
    """Outcome of a streaming run."""

    sent: int = 0
    acked: int = 0
    errors: list[Error] = field(default_factory=list)
    alarms: list[Alarm] = field(default_factory=list)
    completed: bool = False
    cancelled: bool = False


class CharacterCountingStreamer:
    """Stream G-code lines over a Transport using character counting."""

    def __init__(self, transport, rx_buffer_size: int = RX_BUFFER_SIZE) -> None:
        self._transport = transport
        self._limit = rx_buffer_size
        self._inflight = 0
        self._pending: deque[int] = deque()

    @property
    def inflight_bytes(self) -> int:
        """Bytes sent to GRBL but not yet acknowledged."""
        return self._inflight

    def write_realtime(self, data: bytes) -> None:
        """Send a real-time command byte (hold, resume, status query, ...)."""
        self._transport.write(data)

    def _can_send(self, line: str) -> bool:
        size = len(line.encode()) + 1  # payload + newline
        return self._inflight + size <= self._limit

    def _send(self, line: str) -> None:
        data = line.encode() + b"\n"
        self._transport.write(data)
        self._inflight += len(data)
        self._pending.append(len(data))

    def _ack(self) -> None:
        self._inflight -= self._pending.popleft()

    def run(self, lines, stop_event: threading.Event | None = None) -> StreamResult:
        """Stream lines; returns a StreamResult. Never sends past the buffer."""
        result = StreamResult()
        queue = deque(lines)
        while queue or self._pending:
            if stop_event is not None and stop_event.is_set():
                result.cancelled = True
                return result
            if not result.errors and not result.alarms:
                while queue and self._can_send(queue[0]):
                    self._send(queue.popleft())
                    result.sent += 1
            if queue and not self._pending and not self._can_send(queue[0]):
                return result  # head line can never fit: never send it
            try:
                response = self._transport.read_line(timeout=0.2)
            except TimeoutError:
                continue  # loop head re-checks stop_event
            if response is None:
                return result  # transport closed under our feet
            parsed = parse_line(response)
            if isinstance(parsed, Error):
                result.errors.append(parsed)
                self._ack()  # the failed line is acknowledged with error:x
            elif isinstance(parsed, Alarm):
                result.alarms.append(parsed)
                return result  # abort: position may be lost
            elif isinstance(parsed, Ok):
                self._ack()
                result.acked += 1
            # Push messages (welcome, [MSG:...], status) do not acknowledge.
        result.completed = not result.errors and not result.alarms
        return result
