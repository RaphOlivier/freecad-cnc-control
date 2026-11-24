"""Worker thread owning the transport, with a JSON command/event protocol.

The passation rules impose that the GUI never owns the transport: every
machine interaction goes through this worker. Commands in, events out, one
command at a time (streaming runs to completion or until out-of-band cancel).

Command examples: {"cmd": "connect", "params": {"kind": "socket", "host": ...}}
Event examples: {"event": "connected", "version": "1.1h"}

Connection state machine (E8.2): the worker tracks an explicit state,
exposed through "connection_state" events:

    disconnected --connect ok--> connected --stream--> streaming --> connected
    connected  --disconnect--> disconnected
    streaming  --cancel/failure/done--> connected
"""

import json
import queue
import threading

from freecad.cnc_control.core.connection import GrblConnection
from freecad.cnc_control.core.grbl_protocol import Alarm, Error, Ok
from freecad.cnc_control.core.transport import SerialTransport, SocketTransport

DEFAULT_TRANSPORT_FACTORIES = {
    "socket": lambda params: SocketTransport(params["host"], int(params["port"])),
    "serial": lambda params: SerialTransport(
        params["port"], int(params.get("baudrate", 115200))
    ),
}

DISCONNECTED = "disconnected"
CONNECTED = "connected"
STREAMING = "streaming"

# Commands rejected outright while a stream is in flight.
_BUSY_REJECT = ("send", "stream", "disconnect")


def encode_json_line(payload: dict) -> bytes:
    """Encode one protocol message as a JSON line (bytes, newline ended)."""
    return (json.dumps(payload, sort_keys=True) + "\\n").encode()


def decode_json_line(text: str) -> dict:
    """Decode one protocol message from a JSON line."""
    return json.loads(text)


def _response_payload(parsed) -> dict:
    """Flatten an ok/error/ALARM result into a JSON-ready dict."""
    if isinstance(parsed, Ok):
        return {"kind": "ok"}
    if isinstance(parsed, Error):
        return {"kind": "error", "code": parsed.code, "description": parsed.description}
    if isinstance(parsed, Alarm):
        return {"kind": "alarm", "code": parsed.code, "description": parsed.description}
    return {"kind": "unknown", "text": repr(parsed)}


class Worker:
    """Owns the GrblConnection; processes one submitted command at a time."""

    def __init__(self, transport_factories=None, emit=None) -> None:
        self._factories = transport_factories or DEFAULT_TRANSPORT_FACTORIES
        self._emit = emit or (lambda event: None)
        self._commands: queue.Queue = queue.Queue()
        self._stop = threading.Event()
        self._cancel_event = threading.Event()
        self._connection: GrblConnection | None = None
        self._state = DISCONNECTED
        self._state_lock = threading.Lock()

    # --- connection state -------------------------------------------------

    @property
    def state(self) -> str:
        """Current connection state (readable from the GUI thread)."""
        with self._state_lock:
            return self._state

    def _set_state(self, value: str) -> None:
        """Transition the state and announce it; every change is emitted."""
        with self._state_lock:
            previous = self._state
            self._state = value
        if previous != value:
            self._emit({"event": "connection_state", "value": value})

    # --- queue management -------------------------------------------------

    def submit(self, command: dict) -> None:
        """Queue one command dict; processed by run().

        Rejected immediately (with a busy_streaming error event, not queued)
        when a stream is in flight: only cancel, status and shutdown are
        meaningful then.
        """
        cmd = command.get("cmd")
        if cmd in _BUSY_REJECT and self.state == STREAMING:
            self.emit_error("busy_streaming", command=cmd)
            return
        self._commands.put(command)

    def cancel(self) -> None:
        """Out-of-band stream cancellation (like real-time bytes, not queued)."""
        self._cancel_event.set()

    def stop(self) -> None:
        self._stop.set()

    def run(self) -> None:
        # Unconditional initial emission: there is no transition to a state
        # the worker already starts in, but the GUI must still learn it.
        with self._state_lock:
            initial = self._state
        self._emit({"event": "connection_state", "value": initial})
        self._emit({"event": "state", "value": "ready"})
        while not self._stop.is_set():
            try:
                command = self._commands.get(timeout=0.05)
            except queue.Empty:
                continue
            try:
                keep_running = self._dispatch(command)
            except Exception as exc:  # noqa: BLE001 - surfaced as an error event
                self._emit({"event": "error", "code": "internal_error", "message": str(exc)})
                keep_running = True
            if not keep_running:
                break
        self._emit({"event": "state", "value": "stopped"})

    def _dispatch(self, command: dict) -> bool:
        handlers = {
            "connect": self._handle_connect,
            "disconnect": self._handle_disconnect,
            "send": self._handle_send,
            "status": self._handle_status,
            "stream": self._handle_stream,
            "shutdown": self._handle_shutdown,
        }
        handler = handlers.get(command.get("cmd"))
        if handler is None:
            self.emit_error("unknown_command", command=str(command.get("cmd")))
            return True
        return handler(command.get("params") or {})

    def emit_error(self, code: str, **extra) -> None:
        self._emit({"event": "error", "code": code, **extra})

    # --- command handlers -------------------------------------------------

    def _handle_connect(self, params: dict) -> bool:
        if self.state != DISCONNECTED:
            self.emit_error("already_connected", state=self.state)
            return True
        factory = self._factories.get(params.get("kind"))
        if factory is None:
            self.emit_error("unknown_transport", transport=params.get("kind"))
            return True
        try:
            connection = GrblConnection(factory(params))
            timeout = params.get("timeout")
            version = (
                connection.connect(timeout=timeout) if timeout else connection.connect()
            )
        except Exception as exc:  # noqa: BLE001 - surfaced as an error event
            self._connection = None
            self._set_state(DISCONNECTED)
            self.emit_error("connect_failed", message=str(exc))
            return True
        self._connection = connection
        self._set_state(CONNECTED)
        self._emit({"event": "connected", "version": version})
        return True

    def _handle_disconnect(self, _params: dict) -> bool:
        if self.state == STREAMING:
            # Defensive: submit() rejects it earlier; only reachable via a
            # command queued exactly at the streaming boundary.
            self.emit_error("busy_streaming", command="disconnect")
            return True
        if self._connection is None:
            self.emit_error("not_connected")
            return True
        self._connection.close()
        self._connection = None
        self._set_state(DISCONNECTED)
        self._emit({"event": "disconnected"})
        return True

    def _handle_send(self, params: dict) -> bool:
        if self._connection is None:
            self.emit_error("not_connected")
            return True
        line = params.get("line")
        if not isinstance(line, str):
            self.emit_error("invalid_command", command="send")
            return True
        try:
            parsed = self._connection.send_line(line, timeout=params.get("timeout") or 10.0)
        except TimeoutError:
            self.emit_error("response_timeout", command="send")
            return True
        self._emit({"event": "response", **_response_payload(parsed)})
        return True

    def _handle_status(self, params: dict) -> bool:
        if self._connection is None:
            self.emit_error("not_connected")
            return True
        try:
            status = self._connection.poll_status(timeout=params.get("timeout") or 2.0)
        except TimeoutError:
            self.emit_error("response_timeout", command="status")
            return True
        self._emit(
            {
                "event": "status",
                "state": status.state,
                "mpos": list(status.mpos) if status.mpos is not None else None,
            }
        )
        return True

    def _handle_stream(self, params: dict) -> bool:
        if self._connection is None:
            self.emit_error("not_connected")
            return True
        lines = params.get("lines")
        if not isinstance(lines, list):
            self.emit_error("invalid_command", command="stream")
            return True
        self._cancel_event.clear()
        self._set_state(STREAMING)
        result = self._connection.stream(lines, stop_event=self._cancel_event)
        self._set_state(CONNECTED)
        self._emit(
            {
                "event": "stream_done",
                "sent": result.sent,
                "acked": result.acked,
                "completed": result.completed,
                "cancelled": result.cancelled,
                "errors": [_response_payload(e) for e in result.errors],
                "alarms": [_response_payload(a) for a in result.alarms],
            }
        )
        return True

    def _handle_shutdown(self, _params: dict) -> bool:
        self._emit({"event": "bye"})
        return False
