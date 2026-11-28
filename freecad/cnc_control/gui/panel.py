"""Docked control panel: connection, status, real-time controls and jog."""

from freecad.cnc_control.freecad_adapter.host import translate
from freecad.cnc_control.freecad_adapter.qt import QtCore, QtWidgets
from freecad.cnc_control.gui.dialogs import JobDialogs

_CONTEXT = "CncControl"


def _text(source: str) -> str:
    """Translate a user-facing string."""
    return translate(_CONTEXT, source)


class CncControlPanel(QtWidgets.QWidget):
    """Qt panel that only talks to the WorkerBridge."""

    def __init__(self, bridge, parent=None, job_source=None, dialogs=None) -> None:
        super().__init__(parent)
        self._bridge = bridge
        self._job_source = job_source
        self._dialogs = dialogs or JobDialogs()
        self._job_lines: list[str] | None = None
        self._bridge.event_received.connect(self.on_event)
        self._status_timer = QtCore.QTimer(self)
        self._status_timer.setInterval(500)
        self._status_timer.timeout.connect(self._poll_status)
        self._jog_timer = QtCore.QTimer(self)
        self._jog_timer.setInterval(150)
        self._jog_timer.timeout.connect(self._continuous_tick)
        self._jog_axis: str | None = None
        self._jog_sign = 1
        self._build_ui()
        self._connect_signals()

    # --- UI construction --------------------------------------------------

    def _build_ui(self) -> None:
        layout = QtWidgets.QVBoxLayout(self)

        connection = QtWidgets.QGroupBox(_text("Connection"), self)
        form = QtWidgets.QFormLayout(connection)
        self.transport_combo = QtWidgets.QComboBox(connection)
        self.transport_combo.addItem(_text("Serial"), "serial")
        self.transport_combo.addItem(_text("Socket"), "socket")
        self.endpoint_label = QtWidgets.QLabel(connection)
        self.endpoint_edit = QtWidgets.QLineEdit(connection)
        self.port_label = QtWidgets.QLabel(_text("Port"), connection)
        self.port_spin = QtWidgets.QSpinBox(connection)
        self.port_spin.setRange(1, 65535)
        self.port_spin.setValue(15000)
        self.baud_label = QtWidgets.QLabel(_text("Baud rate"), connection)
        self.baud_spin = QtWidgets.QSpinBox(connection)
        self.baud_spin.setRange(1200, 921600)
        self.baud_spin.setValue(115200)
        buttons = QtWidgets.QHBoxLayout()
        self.connect_button = QtWidgets.QPushButton(_text("Connect"), connection)
        self.disconnect_button = QtWidgets.QPushButton(_text("Disconnect"), connection)
        buttons.addWidget(self.connect_button)
        buttons.addWidget(self.disconnect_button)

        form.addRow(_text("Transport"), self.transport_combo)
        form.addRow(self.endpoint_label, self.endpoint_edit)
        form.addRow(self.port_label, self.port_spin)
        form.addRow(self.baud_label, self.baud_spin)
        form.addRow(buttons)
        layout.addWidget(connection)

        status = QtWidgets.QGroupBox(_text("Machine status"), self)
        status_layout = QtWidgets.QFormLayout(status)
        self.state_value = QtWidgets.QLabel(_text("disconnected"), status)
        self.machine_state_value = QtWidgets.QLabel("-", status)
        self.mpos_value = QtWidgets.QLabel("-", status)
        self.version_value = QtWidgets.QLabel("-", status)
        for name, label in (
            ("state_value", _text("Link")),
            ("machine_state_value", _text("State")),
            ("mpos_value", _text("Machine position")),
            ("version_value", _text("GRBL version")),
        ):
            widget = getattr(self, name)
            widget.setObjectName(name)
            status_layout.addRow(label, widget)
        layout.addWidget(status)

        realtime = QtWidgets.QGroupBox(_text("Real-time"), self)
        realtime_layout = QtWidgets.QHBoxLayout(realtime)
        self.hold_button = QtWidgets.QPushButton(_text("Hold"), realtime)
        self.resume_button = QtWidgets.QPushButton(_text("Resume"), realtime)
        self.reset_button = QtWidgets.QPushButton(_text("Reset"), realtime)
        self.jog_cancel_button = QtWidgets.QPushButton(_text("Jog cancel"), realtime)
        for button in (
            self.hold_button,
            self.resume_button,
            self.reset_button,
            self.jog_cancel_button,
        ):
            realtime_layout.addWidget(button)
        layout.addWidget(realtime)

        jog = QtWidgets.QGroupBox(_text("Jog"), self)
        jog_form = QtWidgets.QFormLayout(jog)
        self.step_spin = QtWidgets.QDoubleSpinBox(jog)
        self.step_spin.setRange(0.01, 100.0)
        self.step_spin.setValue(1.0)
        self.feed_spin = QtWidgets.QDoubleSpinBox(jog)
        self.feed_spin.setRange(1.0, 5000.0)
        self.feed_spin.setValue(100.0)
        jog_form.addRow(_text("Step (mm)"), self.step_spin)
        jog_form.addRow(_text("Feed (mm/min)"), self.feed_spin)
        grid = QtWidgets.QGridLayout()
        self.jog_buttons: dict[tuple[str, int], QtWidgets.QPushButton] = {}
        for row, axis in enumerate("XYZ"):
            for column, sign in enumerate((-1, 1)):
                label = f"{axis}-" if sign < 0 else f"{axis}+"
                button = QtWidgets.QPushButton(label, jog)
                button.setObjectName(f"jog_{axis}_{'minus' if sign < 0 else 'plus'}")
                self.jog_buttons[(axis, sign)] = button
                grid.addWidget(button, row, column)
        jog_form.addRow(grid)
        layout.addWidget(jog)

        job = QtWidgets.QGroupBox(_text("CAM job"), self)
        job_layout = QtWidgets.QHBoxLayout(job)
        self.send_job_button = QtWidgets.QPushButton(
            _text("Send selected CAM Job"), job
        )
        self.send_job_button.setObjectName("send_job_button")
        self.job_summary = QtWidgets.QLabel(_text("No job loaded"), job)
        self.job_summary.setObjectName("job_summary")
        job_layout.addWidget(self.send_job_button)
        job_layout.addWidget(self.job_summary)
        layout.addWidget(job)

        self.log_list = QtWidgets.QListWidget(self)
        self.log_list.setObjectName("log_list")
        self.log_list.setMaximumHeight(140)
        layout.addWidget(self.log_list)
        self._on_transport_changed()

    def _connect_signals(self) -> None:
        self.transport_combo.currentIndexChanged.connect(self._on_transport_changed)
        self.connect_button.clicked.connect(self.connect)
        self.disconnect_button.clicked.connect(self.disconnect)
        self.send_job_button.clicked.connect(self.send_job)
        self.hold_button.clicked.connect(lambda: self._bridge.realtime("hold"))
        self.resume_button.clicked.connect(lambda: self._bridge.realtime("resume"))
        self.reset_button.clicked.connect(lambda: self._bridge.realtime("reset"))
        self.jog_cancel_button.clicked.connect(
            lambda: self._bridge.realtime("jog_cancel")
        )
        for (axis, sign), button in self.jog_buttons.items():
            button.pressed.connect(lambda axis=axis, sign=sign: self.start_jog(axis, sign))
            button.released.connect(self.stop_jog)

    # --- user actions -----------------------------------------------------

    def _on_transport_changed(self) -> None:
        serial = self.transport_combo.currentData() == "serial"
        self.endpoint_label.setText(_text("Port") if serial else _text("Host"))
        self.port_label.setVisible(not serial)
        self.port_spin.setVisible(not serial)
        self.baud_label.setVisible(serial)
        self.baud_spin.setVisible(serial)

    def connect(self) -> None:
        """Submit a connect command; no transport is opened by the panel."""
        endpoint = self.endpoint_edit.text().strip()
        if self.transport_combo.currentData() == "serial":
            params = {
                "kind": "serial",
                "port": endpoint,
                "baudrate": int(self.baud_spin.value()),
            }
        else:
            params = {
                "kind": "socket",
                "host": endpoint,
                "port": int(self.port_spin.value()),
            }
        self._bridge.submit({"cmd": "connect", "params": params})

    def disconnect(self) -> None:
        self._bridge.submit({"cmd": "disconnect"})

    def send_job(self) -> None:
        """Post-process the selected CAM job and request a pre-job check."""
        if self._job_source is None:
            self._log(_text("No CAM Job source available"))
            return
        try:
            result = self._job_source()
        except Exception as exc:  # noqa: BLE001 - FreeCAD errors must not crash the panel
            self._log(f"{_text('job_failed')}: {exc}")
            return
        if result is None or not result.lines:
            self._log(_text("No CAM Job selected"))
            return
        self._job_lines = list(result.lines)
        self.job_summary.setText(", ".join(result.operations) or "-")
        if not self._dialogs.confirm_job(result, self):
            self._log(_text("CAM job cancelled"))
            return
        self._bridge.submit(
            {"cmd": "preflight", "params": {"lines": self._job_lines}}
        )

    def _poll_status(self) -> None:
        self._bridge.submit({"cmd": "status"})

    def jog_step(self, axis: str, sign: int) -> None:
        """Submit one explicit incremental jog step."""
        self._bridge.submit(
            {
                "cmd": "jog",
                "params": {
                    "axis": axis,
                    "distance": self.step_spin.value() * sign,
                    "feed": self.feed_spin.value(),
                },
            }
        )

    def start_jog(self, axis: str, sign: int) -> None:
        """Start continuous jog on button press; stop on release/focus loss."""
        if self._jog_timer.isActive():
            return
        self._jog_axis = axis
        self._jog_sign = sign
        self.jog_step(axis, sign)
        self._jog_timer.start()

    def _continuous_tick(self) -> None:
        if self._jog_axis is not None:
            self.jog_step(self._jog_axis, self._jog_sign)

    def stop_jog(self) -> None:
        """Stop continuous jog with a real-time jog-cancel byte."""
        if not self._jog_timer.isActive():
            return
        self._jog_timer.stop()
        self._jog_axis = None
        self._bridge.realtime("jog_cancel")

    # --- event handling ---------------------------------------------------

    def on_event(self, event: dict) -> None:
        """Update widgets from worker events (always on the GUI thread)."""
        kind = event.get("event")
        if kind == "connection_state":
            self.state_value.setText(str(event.get("value", "")))
            if event.get("value") == "disconnected":
                self._status_timer.stop()
        elif kind == "connected":
            self.version_value.setText(str(event.get("version", "")))
            self._status_timer.start()
            self._log(_text("Connected"))
        elif kind == "disconnected":
            self._status_timer.stop()
            self.machine_state_value.setText("-")
            self.mpos_value.setText("-")
            self._log(_text("Disconnected"))
        elif kind == "status":
            self.machine_state_value.setText(str(event.get("state", "")))
            mpos = event.get("mpos")
            if mpos is not None:
                self.mpos_value.setText(", ".join(f"{value:.3f}" for value in mpos))
        elif kind == "error":
            detail = (
                event.get("message")
                or event.get("reasons")
                or event.get("command")
                or ""
            )
            self._log(f"{event.get('code', 'error')}: {detail}")
        elif kind == "jog":
            self._log(
                _text("Jog {axis} {distance} at {feed}").format(
                    axis=event.get("axis", ""),
                    distance=event.get("distance", ""),
                    feed=event.get("feed", ""),
                )
            )
        elif kind == "preflight":
            self._log(
                _text("Preflight: accepted {accepted}, operations {operations}").format(
                    accepted=event.get("accepted", False),
                    operations=", ".join(event.get("operations", [])),
                )
            )
            for reason in event.get("reasons", []):
                self._log(f"{_text('reason')}: {reason}")
            if not event.get("accepted") or self._job_lines is None:
                return
            check_mode = self._dialogs.choose_check_mode(self)
            if check_mode is None:
                self._log(_text("CAM job cancelled"))
                return
            self._bridge.submit(
                {
                    "cmd": "stream",
                    "params": {
                        "lines": self._job_lines,
                        "confirmed": True,
                        "check_mode": check_mode,
                    },
                }
            )
        elif kind == "stream_done":
            self._log(
                _text("Stream: sent {sent}, acked {acked}, completed {completed}").format(
                    sent=event.get("sent", 0),
                    acked=event.get("acked", 0),
                    completed=event.get("completed", False),
                )
            )

    def _log(self, text: str) -> None:
        self.log_list.addItem(text)
        self.log_list.scrollToBottom()

    # --- Qt lifecycle -----------------------------------------------------

    def focusOutEvent(self, event) -> None:
        self.stop_jog()
        super().focusOutEvent(event)

    def hideEvent(self, event) -> None:
        self.stop_jog()
        super().hideEvent(event)
