"""Adapter tests against a fake FreeCAD host, using real headless Qt."""

from freecad.cnc_control.freecad_adapter import attach_dock, translate
from freecad.cnc_control.freecad_adapter.qt import QtCore, QtWidgets


class FakeHost:
    """A real QMainWindow behind the host protocol expected by the adapter."""

    def __init__(self) -> None:
        self.window = QtWidgets.QMainWindow()
        self.added: list[QtWidgets.QDockWidget] = []

    def main_window(self):
        return self.window

    def add_dock_widget(self, dock: QtWidgets.QDockWidget) -> None:
        self.window.addDockWidget(QtCore.Qt.RightDockWidgetArea, dock)
        self.added.append(dock)
        dock.show()


def test_qt_modules_are_available(qapp):
    assert qapp is not None
    assert QtWidgets.QDockWidget is not None
    assert QtCore.Qt.RightDockWidgetArea is not None


def test_attach_dock_creates_one_dock(qapp):
    host = FakeHost()
    dock = QtWidgets.QDockWidget("Panel")
    attached = attach_dock(host, dock, "CncControlPanel")

    assert attached is dock
    assert dock.objectName() == "CncControlPanel"
    assert host.added == [dock]
    assert host.window.dockWidgetArea(dock) == QtCore.Qt.RightDockWidgetArea


def test_attach_dock_reuses_an_existing_dock(qapp):
    host = FakeHost()
    first = attach_dock(host, QtWidgets.QDockWidget("Panel"), "Panel")
    second = attach_dock(host, QtWidgets.QDockWidget("Other"), "Panel")

    assert second is first
    assert host.added == [first]
    assert len(host.window.findChildren(QtWidgets.QDockWidget, "Panel")) == 1


def test_translate_returns_the_source_string(qapp):
    assert translate("CncControl", "Connect") == "Connect"
