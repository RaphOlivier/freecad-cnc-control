"""Workbench lifecycle tests with a fake FreeCADGui and host."""

from freecad.cnc_control.freecad_adapter import workbench as workbench_module
from freecad.cnc_control.freecad_adapter.qt import QtCore
from tests.gui.test_adapter import FakeHost


class FakeBridge(QtCore.QObject):
    """Bridge protocol fake used by the panel."""

    event_received = QtCore.Signal(dict)

    def __init__(self) -> None:
        super().__init__()
        self.started = False

    def start(self) -> None:
        self.started = True

    def submit(self, _command: dict) -> None:
        return

    def realtime(self, _command: str) -> None:
        return

    def cancel(self) -> None:
        return

    def stop(self) -> None:
        return


class FakeGui:
    """Stand-in for FreeCADGui's registration API."""

    Workbench = object

    def __init__(self) -> None:
        self.added: list[object] = []
        self.commands: dict[str, object] = {}

    def addWorkbench(self, instance) -> None:
        self.added.append(instance)

    def addCommand(self, name, command) -> None:
        self.commands[name] = command


def test_workbench_creates_one_dock_and_starts_the_bridge(qapp):
    host = FakeHost()
    bridges: list[FakeBridge] = []

    def factory():
        bridge = FakeBridge()
        bridges.append(bridge)
        return bridge

    wb = workbench_module.CncControlWorkbench(host=host, bridge_factory=factory)
    assert wb.GetClassName() == "Gui::PythonWorkbench"
    assert wb.Icon.endswith("CNCControl.svg")

    wb.Activated()
    wb.Activated()  # idempotent: no second dock or bridge

    assert len(bridges) == 1
    assert bridges[0].started is True
    assert wb._dock is not None
    assert wb._dock.objectName() == "CncControlPanel"
    assert host.added == [wb._dock]


def test_register_workbench_uses_freecadgui(monkeypatch):
    gui = FakeGui()
    monkeypatch.setattr(workbench_module, "_FreeCADGui", gui)

    workbench_module.register_workbench()

    assert len(gui.added) == 1
    assert isinstance(gui.added[0], workbench_module.CncControlWorkbench)


def test_workbench_registers_send_job_command(qapp, monkeypatch):
    gui = FakeGui()
    monkeypatch.setattr(workbench_module, "_FreeCADGui", gui)
    wb = workbench_module.CncControlWorkbench(
        host=FakeHost(), bridge_factory=FakeBridge
    )

    wb.Activated()
    wb.Activated()

    name = "CNCControl_SendJob"
    assert list(gui.commands) == [name]
    command = gui.commands[name]
    assert command.IsActive() is True
    assert command.GetResources()["Pixmap"].endswith("CNCControl.svg")
    called: list[bool] = []
    wb._panel.send_job = lambda: called.append(True)
    command.Activated()
    assert called == [True]
