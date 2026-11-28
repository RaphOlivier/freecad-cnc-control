"""Headless tests for the docked panel's user actions and event updates."""

from freecad.cnc_control.freecad_adapter.qt import QtCore, QtGui
from freecad.cnc_control.gui.panel import CncControlPanel


class FakeBridge(QtCore.QObject):
    """Bridge protocol fake: records commands, emits events on demand."""

    event_received = QtCore.Signal(dict)

    def __init__(self) -> None:
        super().__init__()
        self.submitted: list[dict] = []
        self.realtime_commands: list[str] = []

    def submit(self, command: dict) -> None:
        self.submitted.append(command)

    def realtime(self, command: str) -> None:
        self.realtime_commands.append(command)

    def start(self) -> None:
        return

    def cancel(self) -> None:
        return

    def stop(self) -> None:
        return


def make_panel(qapp):
    bridge = FakeBridge()
    panel = CncControlPanel(bridge)
    return panel, bridge


def test_connect_builds_serial_params(qapp):
    panel, bridge = make_panel(qapp)
    panel.endpoint_edit.setText("loop://")
    panel.baud_spin.setValue(57600)
    panel.connect_button.click()

    assert bridge.submitted == [
        {
            "cmd": "connect",
            "params": {"kind": "serial", "port": "loop://", "baudrate": 57600},
        }
    ]


def test_connect_builds_socket_params(qapp):
    panel, bridge = make_panel(qapp)
    panel.transport_combo.setCurrentIndex(1)
    panel.endpoint_edit.setText("127.0.0.1")
    panel.port_spin.setValue(23232)
    panel.connect_button.click()

    assert bridge.submitted == [
        {
            "cmd": "connect",
            "params": {"kind": "socket", "host": "127.0.0.1", "port": 23232},
        }
    ]


def test_status_event_updates_labels(qapp):
    panel, _bridge = make_panel(qapp)
    panel.on_event({"event": "connected", "version": "1.1h"})
    panel.on_event({"event": "status", "state": "Idle", "mpos": [1.0, 2.0, 3.0]})

    assert panel.version_value.text() == "1.1h"
    assert panel.machine_state_value.text() == "Idle"
    assert panel.mpos_value.text() == "1.000, 2.000, 3.000"


def test_jog_button_sends_one_explicit_step(qapp):
    panel, bridge = make_panel(qapp)
    panel.step_spin.setValue(2.5)
    panel.feed_spin.setValue(200)
    panel.jog_buttons[("X", 1)].click()

    assert bridge.submitted[-1] == {
        "cmd": "jog",
        "params": {"axis": "X", "distance": 2.5, "feed": 200.0},
    }


def test_realtime_buttons_send_out_of_band_commands(qapp):
    panel, bridge = make_panel(qapp)
    panel.hold_button.click()
    panel.resume_button.click()
    panel.reset_button.click()
    panel.jog_cancel_button.click()

    assert bridge.realtime_commands == ["hold", "resume", "reset", "jog_cancel"]


def test_continuous_jog_stops_on_release(qapp):
    panel, bridge = make_panel(qapp)
    button = panel.jog_buttons[("Y", -1)]
    button.pressed.emit()
    panel._continuous_tick()
    button.released.emit()

    assert [command["params"]["axis"] for command in bridge.submitted] == ["Y", "Y"]
    assert [command["params"]["distance"] for command in bridge.submitted] == [-1.0, -1.0]
    assert bridge.realtime_commands == ["jog_cancel"]
    assert not panel._jog_timer.isActive()


def test_focus_loss_stops_continuous_jog(qapp):
    panel, bridge = make_panel(qapp)
    panel.jog_buttons[("Z", 1)].pressed.emit()
    panel.focusOutEvent(QtGui.QFocusEvent(QtCore.QEvent.Type.FocusOut))

    assert bridge.realtime_commands == ["jog_cancel"]
    assert not panel._jog_timer.isActive()


def test_error_event_is_logged(qapp):
    panel, _bridge = make_panel(qapp)
    panel.on_event({"event": "error", "code": "alarm_active", "state": "Alarm"})

    assert panel.log_list.count() == 1
    assert "alarm_active" in panel.log_list.item(0).text()
