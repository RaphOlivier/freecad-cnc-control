"""Worker thread owning the transport, with a JSON command/event protocol.

The passation rules impose that the GUI never owns the transport: every
machine interaction goes through this worker. Commands in, events out, one
command at a time (streaming commands run to completion).

Command examples: {"cmd": "connect", "params": {"kind": "socket", "host": ...}}
Event examples: {"event": "connected", "version": "1.1h"}
"""

import json
import queue
import threading

from freecad.cnc_control.core.connection import GrblConnection
from freecad.cnc_control.core.grbl_protocol import Alarm, Error, Ok
from freecad.cnc_control.core.transport import SocketTransport

DEFAULT_TRANSPORT_FACTORIES = {
    "socket": lambda params: SocketTransport(params["host"], int(params["port"])),
}


def encode_json_line(payload: dict) -> bytes:
    """Encode one protocol message as a JSON line (bytes, newline ended)."""
    return (json.dumps(payload, sort_keys=True) + "\n").encode()


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
        self._connection: GrblConnection | None = None

    def submit(self, command: dict) -> None:
        """Queue one command dict; processed by run()."""
        self._commands.put(command)

    def stop(self) -> None:
        self._stop.set()

    def run(self) -> None:
        self._emit({"event": "state", "value": "ready"})
        while not self._stop.is_set():
            try:
                command = self._commands.get(timeout=0.05)
            except queue.Empty:
                continue
            if not self._dispatch(command):
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
            self._emit(
                {"event": "error", "code": "unknown_command", "command": command.get("cmd")}
            )
            return True
        return handler(command.get("params") or {})

    def _handle_connect(self, params: dict) -> bool:
        factory = self._factories.get(params.get("kind"))
        if factory is None:
            self._emit(
                {"event": "error", "code": "unknown_transport", "transport": params.get("kind")}
            )
            return True
        try:
            connection = GrblConnection(factory(params))
            version = connection.connect()
        except Exception as exc:  # noqa: BLE001 - surfaced as an error event
            self._connection = None
            self._emit({"event": "error", "code": "connect_failed", "message": str(exc)})
            return True
        self._connection = connection
        self._emit({"event": "connected", "version": version})
        return True

    def _handle_disconnect(self, _params: dict) -> bool:
        if self._connection is None:
            self._emit({"event": "error", "code": "not_connected"})
            return True
        self._connection.close()
        self._connection = None
        self._emit({"event": "disconnected"})
        return True

    def _handle_send(self, params: dict) -> bool:
        if self._connection is None:
            self._emit({"event": "error", "code": "not_connected"})
            return True
        line = params.get("line")
        if not isinstance(line, str):
            self._emit({"event": "error", "code": "invalid_command", "command": "send"})
            return True
        payload = _response_payload(self._connection.send_line(line))
        self._emit({"event": "response", **payload})
        return True

    def _handle_status(self, _params: dict) -> bool:
        if self._connection is None:
            self._emit({"event": "error", "code": "not_connected"})
            return True
        status = self._connection.poll_status()
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
            self._emit({"event": "error", "code": "not_connected"})
            return True
        lines = params.get("lines")
        if not isinstance(lines, list):
            self._emit({"event": "error", "code": "invalid_command", "command": "stream"})
            return True
        result = self._connection.stream(lines)
        self._emit(
            {
                "event": "stream_done",
                "sent": result.sent,
                "acked": result.acked,
                "completed": result.completed,
                "errors": [_response_payload(e) for e in result.errors],
                "alarms": [_response_payload(a) for a in result.alarms],
            }
        )
        return True

    def _handle_shutdown(self, _params: dict) -> bool:
        self._emit({"event": "bye"})
        return False
