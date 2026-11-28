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

Safety gate (post-review E8): every stream must be preceded, on this worker,
by an accepted preflight for the exact same lines. The check is repeated with
fresh ``$$`` and status data at stream time; a real run additionally needs
``confirmed: true``. Check mode streams need preflight but no confirmation.
"""

import json
import queue
import threading

from freecad.cnc_control.core.connection import GrblConnection
from freecad.cnc_control.core.gcode import analyze
from freecad.cnc_control.core.grbl_protocol import Alarm, Error, Ok
from freecad.cnc_control.core.preflight import (
    MachineLimits,
    check_job,
    validate_job_lines,
)
from freecad.cnc_control.core.streamer import StreamResult
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
# Shutdown is deliberately absent: it is out-of-band and cancels the stream.
_BUSY_REJECT = ("send", "stream", "disconnect")


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
        self._cancel_event = threading.Event()
        self._connection: GrblConnection | None = None
        self._state = DISCONNECTED
        self._state_lock = threading.Lock()
        self._approved_job: tuple[tuple[str, ...], bool] | None = None
        self._rejected_job: tuple[tuple[str, ...], list[str]] | None = None

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
        meaningful then. Shutdown is out-of-band and cancels the stream.
        """
        cmd = command.get("cmd")
        if cmd == "shutdown":
            self.stop()
            return
        if cmd in _BUSY_REJECT and self.state == STREAMING:
            self.emit_error("busy_streaming", command=cmd)
            return
        self._commands.put(command)

    def cancel(self) -> None:
        """Out-of-band stream cancellation (like real-time bytes, not queued).

        The flag is latched: a cancel issued before the stream handler starts
        cancels that stream instead of being silently erased.
        """
        self._cancel_event.set()

    def stop(self) -> None:
        """Stop the worker and cancel any in-flight stream immediately."""
        self._stop.set()
        self._cancel_event.set()
        self._emit({"event": "bye"})

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
            "settings": self._handle_settings,
            "preflight": self._handle_preflight,
            "stream": self._handle_stream,
        }
        handler = handlers.get(command.get("cmd"))
        if handler is None:
            self.emit_error("unknown_command", command=str(command.get("cmd")))
            return True
        return handler(command.get("params") or {})

    def emit_error(self, code: str, **extra) -> None:
        self._emit({"event": "error", "code": code, **extra})

    # --- safety helpers ---------------------------------------------------

    def _prepare_job(self, params: dict, command: str):
        """Analyse and check a program with fresh controller data."""
        lines = params.get("lines")
        if not isinstance(lines, list):
            self.emit_error("invalid_command", command=command)
            return None
        require_confirmation = params.get("require_confirmation", True)
        if not isinstance(require_confirmation, bool):
            self.emit_error("invalid_command", command=command)
            return None
        reasons = validate_job_lines(lines)
        if reasons:
            self.emit_error("invalid_job_lines", reasons=reasons)
            return None
        analysis = analyze(lines)
        try:
            settings = self._connection.read_settings(
                timeout=params.get("timeout") or 10.0
            )
            offset = self._connection.work_offset(
                timeout=params.get("status_timeout") or 2.0
            )
        except (TimeoutError, ConnectionError) as exc:
            self.emit_error("preflight_unavailable", message=str(exc))
            return None
        limits = MachineLimits.from_settings(settings)
        result = check_job(
            analysis,
            limits,
            require_confirmation=require_confirmation,
            work_offset=offset,
        )
        return tuple(lines), result

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
            self._approved_job = None
            self._rejected_job = None
            self._set_state(DISCONNECTED)
            self.emit_error("connect_failed", message=str(exc))
            return True
        self._connection = connection
        self._approved_job = None
        self._rejected_job = None
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
        self._approved_job = None
        self._rejected_job = None
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
        except (TimeoutError, ConnectionError):
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
        except (TimeoutError, ConnectionError):
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

    def _handle_settings(self, params: dict) -> bool:
        if self._connection is None:
            self.emit_error("not_connected")
            return True
        try:
            settings = self._connection.read_settings(
                timeout=params.get("timeout") or 10.0
            )
        except (TimeoutError, ConnectionError):
            self.emit_error("response_timeout", command="settings")
            return True
        limits = MachineLimits.from_settings(settings)
        self._emit(
            {
                "event": "settings",
                "values": settings,
                "limits": limits.as_dict() if limits is not None else None,
            }
        )
        return True

    def _handle_preflight(self, params: dict) -> bool:
        if self._connection is None:
            self.emit_error("not_connected")
            return True
        prepared = self._prepare_job(params, "preflight")
        if prepared is None:
            self._approved_job = None
            self._rejected_job = None
            return True
        key, result = prepared
        if result.accepted:
            self._approved_job = (key, result.requires_confirmation)
            self._rejected_job = None
        else:
            self._approved_job = None
            self._rejected_job = (key, list(result.reasons))
        self._emit({"event": "preflight", **result.as_dict()})
        return True

    def _handle_stream(self, params: dict) -> bool:
        if self._connection is None:
            self.emit_error("not_connected")
            return True
        if self.state == STREAMING:
            self.emit_error("busy_streaming", command="stream")
            return True
        lines = params.get("lines")
        if not isinstance(lines, list):
            self.emit_error("invalid_command", command="stream")
            return True
        check_mode = params.get("check_mode", False)
        confirmed = params.get("confirmed", False)
        if not isinstance(check_mode, bool) or not isinstance(confirmed, bool):
            self.emit_error("invalid_command", command="stream")
            return True

        key = tuple(lines)
        if self._approved_job is None or self._approved_job[0] != key:
            if self._rejected_job is not None and self._rejected_job[0] == key:
                self.emit_error(
                    "preflight_rejected", reasons=list(self._rejected_job[1])
                )
            else:
                self.emit_error("preflight_required", command="stream")
            return True
        prepared = self._prepare_job(
            {
                "lines": lines,
                "require_confirmation": self._approved_job[1],
                "timeout": params.get("timeout"),
                "status_timeout": params.get("status_timeout"),
            },
            "stream",
        )
        if prepared is None:
            self._approved_job = None
            self._rejected_job = None
            return True
        _, result = prepared
        if not result.accepted:
            self._approved_job = None
            self._rejected_job = (key, list(result.reasons))
            self.emit_error("preflight_rejected", reasons=result.reasons)
            return True
        if not check_mode and result.requires_confirmation and not confirmed:
            self.emit_error("confirmation_required", command="stream")
            return True

        if self._cancel_event.is_set():
            # A cancel issued before this point is latched: send nothing.
            self._cancel_event.clear()
            self._approved_job = None
            self._rejected_job = None
            self._emit(
                {
                    "event": "stream_done",
                    "sent": 0,
                    "acked": 0,
                    "completed": False,
                    "cancelled": True,
                    "check_mode": False,
                    "errors": [],
                    "alarms": [],
                }
            )
            return True

        if check_mode:
            try:
                response = self._connection.send_line("$C")
            except (TimeoutError, ConnectionError) as exc:
                self._approved_job = None
                self._rejected_job = None
                self.emit_error("check_mode_on_failed", message=str(exc))
                return True
            if not isinstance(response, Ok):
                self._approved_job = None
                self._rejected_job = None
                self.emit_error(
                    "check_mode_on_failed", response=_response_payload(response)
                )
                return True
            self._emit({"event": "check_mode", "enabled": True})

        result_stream = StreamResult()
        self._set_state(STREAMING)
        try:
            result_stream = self._connection.stream(
                lines, stop_event=self._cancel_event
            )
        except (TimeoutError, ConnectionError) as exc:
            self.emit_error("stream_failed", message=str(exc))
        finally:
            self._set_state(CONNECTED)
            self._approved_job = None
            self._rejected_job = None
            self._cancel_event.clear()
            if check_mode:
                try:
                    off_response = self._connection.send_line("$C")
                except (TimeoutError, ConnectionError) as exc:
                    self.emit_error("check_mode_off_failed", message=str(exc))
                else:
                    if isinstance(off_response, Ok):
                        self._emit({"event": "check_mode", "enabled": False})
                    else:
                        self.emit_error(
                            "check_mode_off_failed",
                            response=_response_payload(off_response),
                        )

        self._emit(
            {
                "event": "stream_done",
                "sent": result_stream.sent,
                "acked": result_stream.acked,
                "completed": result_stream.completed,
                "cancelled": result_stream.cancelled,
                "check_mode": check_mode,
                "errors": [_response_payload(e) for e in result_stream.errors],
                "alarms": [_response_payload(a) for a in result_stream.alarms],
            }
        )
        return True
